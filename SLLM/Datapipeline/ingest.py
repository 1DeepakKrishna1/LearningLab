"""Build the SLLM knowledge base.

Walks the documents folder, extracts text from every supported file, splits it
into overlapping chunks, embeds each chunk with a local Ollama embedding model,
and stores the vectors + text + source metadata in a persistent Chroma store.

Usage:
    python ingest.py                 # ingest config.DOCS_FOLDER (rebuilds clean)
    python ingest.py --folder ./mydocs
    python ingest.py --keep          # add to the existing store instead of resetting

Prerequisites:
    ollama serve
    ollama pull nomic-embed-text
"""
import argparse
import sys
from pathlib import Path

import chromadb
from ollama import Client
from tqdm import tqdm

import config
from chunker import chunk_text
from loaders import load_file


def gather_files(folder: Path):
    if not folder.exists():
        sys.exit(f"[error] documents folder does not exist: {folder}")
    files = [
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in config.SUPPORTED_SUFFIXES
    ]
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into the SLLM vector store")
    parser.add_argument("--folder", type=Path, default=config.DOCS_FOLDER,
                        help="Folder of source documents to ingest")
    parser.add_argument("--keep", action="store_true",
                        help="Append to the existing collection instead of rebuilding it")
    args = parser.parse_args()

    folder = args.folder.resolve()
    print(f"Documents folder : {folder}")
    print(f"Vector store     : {config.VECTORSTORE_DIR}")
    print(f"Embedding model  : {config.EMBED_MODEL} @ {config.OLLAMA_HOST}")

    files = gather_files(folder)
    if not files:
        sys.exit(f"[error] no supported files found under {folder}\n"
                 f"        supported: {', '.join(sorted(config.SUPPORTED_SUFFIXES))}")
    print(f"Found {len(files)} file(s) to ingest.\n")

    ollama = Client(host=config.OLLAMA_HOST)
    config.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=str(config.VECTORSTORE_DIR))

    if not args.keep:
        try:
            chroma.delete_collection(config.COLLECTION_NAME)
            print(f"Reset existing collection '{config.COLLECTION_NAME}'.")
        except Exception:
            pass
    collection = chroma.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    for path in files:
        rel = path.relative_to(folder)
        text = load_file(path)
        chunks = chunk_text(text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        if not chunks:
            print(f"  [skip] {rel} (no extractable text)")
            continue

        ids, docs, metas, embeddings = [], [], [], []
        for i, chunk in enumerate(tqdm(chunks, desc=str(rel), unit="chunk", leave=False)):
            resp = ollama.embeddings(model=config.EMBED_MODEL, prompt=chunk)
            embeddings.append(resp["embedding"])
            ids.append(f"{rel}::chunk-{i}")
            docs.append(chunk)
            metas.append({"source": str(rel), "chunk": i, "type": path.suffix.lower()})

        # Add in batches to keep individual calls small.
        BATCH = 100
        for j in range(0, len(ids), BATCH):
            collection.add(
                ids=ids[j:j + BATCH],
                documents=docs[j:j + BATCH],
                metadatas=metas[j:j + BATCH],
                embeddings=embeddings[j:j + BATCH],
            )
        total_chunks += len(chunks)
        print(f"  [ok]   {rel}  ->  {len(chunks)} chunk(s)")

    print(f"\nDone. {total_chunks} chunk(s) stored in collection "
          f"'{config.COLLECTION_NAME}' ({collection.count()} total).")
    print("Your SLLM knowledge base is ready. Start the Backend next.")


if __name__ == "__main__":
    main()
