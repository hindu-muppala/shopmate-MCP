from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatusSchema(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class OrderItemCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    user_id: str
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemRead(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: str
    user_id: str
    status: OrderStatusSchema
    total: Decimal
    currency: str
    created_at: datetime
    items: list[OrderItemRead]

    model_config = ConfigDict(from_attributes=True)
