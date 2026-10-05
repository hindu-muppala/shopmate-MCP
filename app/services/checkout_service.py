from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import CartNotFound, InvalidRequest
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.checkout import CheckoutRead
from app.schemas.order import OrderRead
from app.services.inventory_service import InventoryService


class CheckoutService:
    def __init__(
        self,
        session: AsyncSession,
        carts: CartRepository,
        orders: OrderRepository,
        inventory: InventoryService,
    ) -> None:
        self.session = session
        self.carts = carts
        self.orders = orders
        self.inventory = inventory

    async def process_checkout(self, user_id: str) -> CheckoutRead:
        if self.session.in_transaction():
            order = await self._create_order(user_id)
            await self.session.commit()
        else:
            async with self.session.begin():
                order = await self._create_order(user_id)

        return CheckoutRead(order=OrderRead.model_validate(order))

    async def _create_order(self, user_id: str) -> Order:
        user = await self.session.get(User, user_id)
        if user is None or not user.is_active:
            raise InvalidRequest("User account was not found or is inactive.")
        items = await self.carts.get_cart_by_user_id(user_id)
        if not items:
            raise CartNotFound("Your cart is empty.")

        total = Decimal("0.00")
        currencies: set[str] = set()
        order_items: list[OrderItem] = []
        for item in items:
            product = item.product
            unit_price, currency = await self.inventory.decrement_stock(
                product.id, product.sku, item.quantity
            )
            total += unit_price * item.quantity
            currencies.add(currency)
            order_items.append(
                OrderItem(
                    product_id=product.id,
                    sku=product.sku,
                    product_name=product.name,
                    quantity=item.quantity,
                    unit_price=unit_price,
                )
            )

        if len(currencies) != 1:
            raise InvalidRequest("A cart cannot contain items in different currencies.")
        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            total=total,
            currency=currencies.pop(),
            items=order_items,
        )
        await self.orders.create_order(order)
        await self.carts.clear_cart(user_id)
        return order
