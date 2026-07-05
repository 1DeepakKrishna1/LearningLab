"""
Inventory Dummy REST API (FastAPI)
===================================

Entities: suppliers, warehouses, categories, products, orders
Each entity supports:
    GET    /<entity>          -> list all
    GET    /<entity>/{id}     -> get one
    POST   /<entity>          -> create
    DELETE /<entity>/{id}     -> delete

Swagger UI : http://localhost:<PORT>/docs
ReDoc      : http://localhost:<PORT>/redoc
OpenAPI    : http://localhost:<PORT>/openapi.json

Port is configurable via the PORT environment variable (default 8002).
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
    title="Inventory API",
    description=(
        "Dummy inventory REST API with suppliers, warehouses, categories, products and orders.\n\n"
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
class Supplier(BaseModel):
    id: Optional[int] = None
    name: str
    contact_email: Optional[str] = None


class Warehouse(BaseModel):
    id: Optional[int] = None
    name: str
    location: Optional[str] = None
    capacity: int = 0


class Category(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None


class Product(BaseModel):
    id: Optional[int] = None
    name: str
    sku: Optional[str] = None
    supplier_id: Optional[int] = None
    category_id: Optional[int] = None
    price: float = 0.0
    stock: int = 0


class Order(BaseModel):
    id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: int = 1
    status: str = "PENDING"
    customer_name: Optional[str] = None


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
register_crud("suppliers", Supplier, [
    {"name": "Acme Corp", "contact_email": "sales@acme.com"},
    {"name": "Globex", "contact_email": "info@globex.com"},
])
register_crud("warehouses", Warehouse, [
    {"name": "North DC", "location": "Chicago", "capacity": 10000},
    {"name": "South DC", "location": "Dallas", "capacity": 8000},
])
register_crud("categories", Category, [
    {"name": "Electronics", "description": "Electronic goods"},
    {"name": "Apparel", "description": "Clothing and accessories"},
])
register_crud("products", Product, [
    {"name": "Wireless Mouse", "sku": "WM-001", "supplier_id": 1, "category_id": 1, "price": 19.99, "stock": 250},
    {"name": "T-Shirt", "sku": "TS-010", "supplier_id": 2, "category_id": 2, "price": 9.99, "stock": 500},
])
register_crud("orders", Order, [
    {"product_id": 1, "quantity": 3, "status": "SHIPPED", "customer_name": "Alice Smith"},
    {"product_id": 2, "quantity": 10, "status": "PENDING", "customer_name": "Bob Jones"},
])


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "Inventory API",
        "docs": "/docs",
        "entities": ["suppliers", "warehouses", "categories", "products", "orders"],
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
