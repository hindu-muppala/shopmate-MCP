from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import CartItem
from app.models.product import Product


class CartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_cart_by_user_id(self, user_id: str) -> list[CartItem]:
        result = await self.session.scalars(
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.id)
        )
        return list(result)

    async def get_item(self, user_id: str, product_id: str) -> CartItem | None:
        return await self.session.scalar(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
            )
        )

    async def add_item(
        self, user_id: str, product: Product, quantity: int
    ) -> CartItem:
        item = await self.get_item(user_id, product.id)
        if item is None:
            item = CartItem(user_id=user_id, product_id=product.id, quantity=quantity)
            self.session.add(item)
        else:
            item.quantity += quantity
        await self.session.flush()
        return item

    async def remove_item(self, user_id: str, sku: str) -> bool:
        item = await self.session.scalar(
            select(CartItem)
            .join(Product)
            .where(CartItem.user_id == user_id, Product.sku == sku)
        )
        if item is None:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def clear_cart(self, user_id: str) -> None:
        for item in await self.get_cart_by_user_id(user_id):
            await self.session.delete(item)
        await self.session.flush()
