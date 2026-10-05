from app.exceptions import InvalidOrderTransition, OrderNotFound
from app.models.order import Order, OrderStatus
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderRead

_ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    async def get_order_status(
        self, order_id: str, user_id: str | None = None
    ) -> OrderRead:
        order = await self.repository.get_order(order_id)
        if order is None or (user_id is not None and order.user_id != user_id):
            raise OrderNotFound(f"Order '{order_id}' was not found.")
        return OrderRead.model_validate(order)

    async def get_order_history(self, user_id: str) -> list[OrderRead]:
        return [
            OrderRead.model_validate(order)
            for order in await self.repository.get_order_history(user_id)
        ]

    async def update_status(self, order: Order, status: OrderStatus) -> OrderRead:
        if status not in _ALLOWED_TRANSITIONS[order.status]:
            raise InvalidOrderTransition(
                f"Cannot change order status from {order.status.value} to {status.value}."
            )
        order.status = status
        await self.repository.session.commit()
        return OrderRead.model_validate(order)
