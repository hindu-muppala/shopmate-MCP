from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    quantity: int = Field(default=0, ge=0)
    category_id: int | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class ProductRead(BaseModel):
    id: str
    sku: str
    name: str
    description: str | None
    price: Decimal
    currency: str
    quantity: int
    attributes: dict[str, str]
    category: CategoryRead | None

    model_config = ConfigDict(from_attributes=True)
