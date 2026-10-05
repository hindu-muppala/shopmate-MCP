from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.product import Product
from app.repositories.base import CRUDRepository


class ProductRepository(CRUDRepository[Product]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Product)

    async def get_product_by_id(self, product_id: str) -> Product | None:
        statement = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        )
        return await self.session.scalar(statement)

    async def get_product_by_sku(self, sku: str) -> Product | None:
        return await self.session.scalar(select(Product).where(Product.sku == sku))

    async def search_products(
        self,
        query: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        category: str | None = None,
        color: str | None = None,
        size: str | None = None,
        limit: int = 10,
    ) -> list[Product]:
        statement = select(Product).options(selectinload(Product.category))
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(Product.name.ilike(pattern), Product.description.ilike(pattern))
            )
        if min_price is not None:
            statement = statement.where(Product.price >= min_price)
        if max_price is not None:
            statement = statement.where(Product.price <= max_price)
        if category:
            statement = statement.join(Product.category).where(
                or_(Category.slug.ilike(category), Category.name.ilike(category))
            )
        if color:
            statement = statement.where(
                Product.attributes["color"].as_string().ilike(color)
            )
        if size:
            statement = statement.where(
                Product.attributes["size"].as_string().ilike(size)
            )
        statement = statement.order_by(Product.name).limit(limit)
        result = await self.session.scalars(statement)
        return list(result)
