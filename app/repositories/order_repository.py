from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_order(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_order(self, order_id: str) -> Order | None:
        return await self.session.scalar(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )

    async def get_order_history(self, user_id: str) -> list[Order]:
        result = await self.session.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return list(result)
