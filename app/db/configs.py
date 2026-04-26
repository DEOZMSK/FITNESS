"""Seed configuration for database entities."""

from __future__ import annotations

from app.data.products import products
from app.data.reviews import reviews

SEED_PRODUCTS: list[dict[str, object]] = [
    {
        "code": str(item["code"]),
        "name": str(item["name"]),
        "description": str(item["description"]),
        "price": int(item["price"]),
        "currency": str(item.get("currency", "RUB")),
        "is_active": int(bool(item.get("is_active", True))),
    }
    for item in products
]

SEED_REVIEWS: list[dict[str, object]] = [
    {
        "author_name": str(item["author_name"]),
        "rating": int(item["rating"]),
        "text": str(item["text"]),
        "is_published": int(bool(item.get("is_published", True))),
    }
    for item in reviews
]
