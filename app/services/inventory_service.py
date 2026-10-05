from decimal import Decimal

from app.exceptions import InsufficientStock, InvalidRequest, ProductNotFound
from app.repositories.inventory_repository import InventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    async def check_stock_level(self, sku: str, quantity: int = 1) -> dict[str, object]:
        if quantity < 1:
            raise InvalidRequest("Quantity must be greater than zero.")
        available = await self.repository.check_stock_level(sku)
        if available is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        return {
            "sku": sku,
            "requested_quantity": quantity,
            "available_quantity": available,
            "available": available >= quantity,
        }

    async def decrement_stock(
        self, product_id: str, sku: str, quantity: int
    ) -> tuple[Decimal, str]:
        if quantity < 1:
            raise InvalidRequest("Quantity must be greater than zero.")
        price_and_currency = await self.repository.decrement_stock(
            product_id, quantity
        )
        if price_and_currency is None:
            available = await self.repository.check_stock_level(sku)
            if available is None:
                raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
            raise InsufficientStock(
                f"Only {available} unit(s) of '{sku}' remain in stock."
            )
        return price_and_currency
