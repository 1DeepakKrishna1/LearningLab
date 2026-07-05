"""
Bookstore Dummy REST API (FastAPI)
===================================

Entities: authors, publishers, categories, books, customers
Each entity supports:
    GET    /<entity>          -> list all
    GET    /<entity>/{id}     -> get one
    POST   /<entity>          -> create
    DELETE /<entity>/{id}     -> delete

Swagger UI : http://localhost:<PORT>/docs
ReDoc      : http://localhost:<PORT>/redoc
OpenAPI    : http://localhost:<PORT>/openapi.json

Port is configurable via the PORT environment variable (default 8001).
"""
import os
from itertools import count
from typing import Dict, List, Optional, Type

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from auth import LoginRequest, TokenResponse, login, require_auth

app = FastAPI(
    title="Bookstore API",
    description=(
        "Dummy bookstore REST API with authors, publishers, categories, books and customers.\n\n"
        "**Authentication (either one):**\n"
        "- API Key header: `X-API-Key: my-secret-api-key`\n"
        "- JWT: call `POST /auth/login` (admin/password), then send `Authorization: Bearer <token>`"
    ),
    version="1.0.0",
)


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def auth_login(req: LoginRequest):
    """Exchange username/password (default admin/password) for a JWT."""
    return login(req)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class Author(BaseModel):
    id: Optional[int] = None
    name: str
    country: Optional[str] = None


class Publisher(BaseModel):
    id: Optional[int] = None
    name: str
    city: Optional[str] = None


class Category(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None


class Book(BaseModel):
    id: Optional[int] = None
    title: str
    author_id: Optional[int] = None
    publisher_id: Optional[int] = None
    category_id: Optional[int] = None
    price: float = 0.0
    isbn: Optional[str] = None


class Customer(BaseModel):
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    loyalty_points: int = 0


# ---------------------------------------------------------------------------
# Generic in-memory CRUD route factory
# ---------------------------------------------------------------------------
def register_crud(entity: str, model: Type[BaseModel], seed: List[dict]) -> None:
    """Register list / get / create / delete routes for an entity."""
    store: Dict[int, dict] = {}
    ids = count(1)

    for item in seed:
        new_id = next(ids)
        item["id"] = new_id
        store[new_id] = item

    tag = entity.capitalize()
    guard = [Depends(require_auth)]

    @app.get(f"/{entity}", response_model=List[model], tags=[tag], dependencies=guard)
    def list_items():
        return list(store.values())

    @app.get(f"/{entity}/{{item_id}}", response_model=model, tags=[tag], dependencies=guard)
    def get_item(item_id: int):
        if item_id not in store:
            raise HTTPException(status_code=404, detail=f"{tag} {item_id} not found")
        return store[item_id]

    @app.post(f"/{entity}", response_model=model, status_code=201, tags=[tag], dependencies=guard)
    def create_item(payload: model):
        data = payload.model_dump()
        new_id = next(ids)
        data["id"] = new_id
        store[new_id] = data
        return data

    @app.delete(f"/{entity}/{{item_id}}", tags=[tag], dependencies=guard)
    def delete_item(item_id: int):
        if item_id not in store:
            raise HTTPException(status_code=404, detail=f"{tag} {item_id} not found")
        del store[item_id]
        return {"deleted": item_id}


# ---------------------------------------------------------------------------
# Register the five entities with some seed data
# ---------------------------------------------------------------------------
register_crud("authors", Author, [
    {"name": "George Orwell", "country": "UK"},
    {"name": "Jane Austen", "country": "UK"},
])
register_crud("publishers", Publisher, [
    {"name": "Penguin Books", "city": "London"},
    {"name": "HarperCollins", "city": "New York"},
])
register_crud("categories", Category, [
    {"name": "Fiction", "description": "Fictional works"},
    {"name": "Non-Fiction", "description": "Factual works"},
])
register_crud("books", Book, [
    {"title": "1984", "author_id": 1, "publisher_id": 1, "category_id": 1, "price": 12.99, "isbn": "978-0451524935"},
    {"title": "Pride and Prejudice", "author_id": 2, "publisher_id": 2, "category_id": 1, "price": 9.99, "isbn": "978-1503290563"},
])
register_crud("customers", Customer, [
    {"name": "Alice Smith", "email": "alice@example.com", "loyalty_points": 100},
    {"name": "Bob Jones", "email": "bob@example.com", "loyalty_points": 50},
])


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "Bookstore API",
        "docs": "/docs",
        "entities": ["authors", "publishers", "categories", "books", "customers"],
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
