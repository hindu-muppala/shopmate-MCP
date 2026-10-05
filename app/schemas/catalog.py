from decimal import Decimal

from pydantic import BaseModel, Field


class ProductSearchInput(BaseModel):
    query: str | None = None
    category: str | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    color: str | None = None
    size: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class ProductResult(BaseModel):
    product_id: str
    sku: str
    name: str
    category: str | None
    price: Decimal
    currency: str = "INR"
    available: bool
    attributes: dict[str, str] = Field(default_factory=dict)
