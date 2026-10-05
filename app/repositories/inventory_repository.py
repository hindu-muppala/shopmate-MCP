from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check_stock_level(self, sku: str) -> int | None:
        product = await self.session.scalar(select(Product).where(Product.sku == sku))
        return product.quantity if product is not None else None

    async def decrement_stock(
        self, product_id: str, quantity: int
    ) -> tuple[Decimal, str] | None:
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id, Product.quantity >= quantity)
            .values(quantity=Product.quantity - quantity)
            .returning(Product.price, Product.currency)
        )
        row = result.one_or_none()
        return (row.price, row.currency) if row is not None else None
