"""Google Drive ingester using OAuth2 / service account credentials."""

from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from src.ingestion.base import BaseIngester
from src.ingestion.deduplicator import Deduplicator
from src.models.schemas import DocumentSource, SourceType
from src.storage.file_store import FileStore
from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics
from src.utils.retry import retry_with_backoff
from src.utils.security import SecureConfig

logger = get_logger(__name__)


class GDriveIngester(BaseIngester):
    """Ingest PDFs from a Google Drive folder (supports OAuth2 and service accounts)."""

    MIME_PDF = "application/pdf"
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(
        self,
        config: SecureConfig,
        file_store: FileStore,
        deduplicator: Deduplicator,
        metrics: PipelineMetrics,
    ) -> None:
        super().__init__(file_store, deduplicator, metrics)
        self.config = config
        self._service = None
        self._tmp_dir = tempfile.mkdtemp(prefix="gdrive_")

    def _get_service(self):
        """Lazily initialise the Drive API client."""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2 import service_account
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError as e:
            raise ImportError(
                "Google API packages not installed. Run: pip install google-auth google-api-python-client google-auth-oauthlib"
            ) from e

        creds = None
        token_file = self.config.settings.gdrive_token_file
        creds_file = self.config.settings.gdrive_credentials_file

        if Path(token_file).exists():
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_file, "w") as f:
                f.write(creds.to_json())

        self._service = build("drive", "v3", credentials=creds)
        return self._service

    def discover(self, folder_id: Optional[str] = None, **kwargs) -> Iterator[DocumentSource]:
        """List all PDFs in the specified Google Drive folder."""
        folder_id = folder_id or self.config.settings.gdrive_folder_id
        if not folder_id:
            logger.error("gdrive_folder_id_not_configured")
            return

        service = self._get_service()
        page_token = None

        while True:
            query = f"'{folder_id}' in parents and mimeType='{self.MIME_PDF}' and trashed=false"
            response = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, size, modifiedTime)",
                    pageToken=page_token,
                )
                .execute()
            )

            for item in response.get("files", []):
                modified = None
                if item.get("modifiedTime"):
                    modified = datetime.fromisoformat(
                        item["modifiedTime"].replace("Z", "+00:00")
                    )
                yield DocumentSource(
                    source_type=SourceType.GDRIVE,
                    source_path=f"gdrive://{item['id']}",
                    file_name=item["name"],
                    file_size_bytes=int(item.get("size", 0)),
                    last_modified=modified,
                    remote_id=item["id"],
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    @retry_with_backoff(max_attempts=3)
    def _fetch_local(self, source: DocumentSource) -> str:
        """Download a Drive file to a temp directory."""
        from googleapiclient.http import MediaIoBaseDownload

        service = self._get_service()
        file_id = source.remote_id
        dest_path = os.path.join(self._tmp_dir, source.file_name)

        request = service.files().get_media(fileId=file_id)
        with open(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        logger.info("gdrive_file_downloaded", file=source.file_name, dest=dest_path)
        return dest_path
