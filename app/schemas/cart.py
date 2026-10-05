from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartUpdate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0)


class CartItemRead(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class CartRead(BaseModel):
    user_id: str
    items: list[CartItemRead]
    total: Decimal
    currency: str = "INR"
