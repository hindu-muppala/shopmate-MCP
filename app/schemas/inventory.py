from pydantic import BaseModel, Field


class InventoryCheck(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    quantity: int = Field(default=1, gt=0)
