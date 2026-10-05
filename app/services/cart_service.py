from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientStock, InvalidRequest, ProductNotFound
from app.models.user import User
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import CartItemRead, CartRead


class CartService:
    def __init__(
        self,
        session: AsyncSession,
        carts: CartRepository,
        products: ProductRepository,
    ) -> None:
        self.session = session
        self.carts = carts
        self.products = products

    async def add_to_cart(self, user_id: str, sku: str, quantity: int) -> CartRead:
        if quantity < 1:
            raise InvalidRequest("Quantity must be greater than zero.")
        user = await self.session.get(User, user_id)
        if user is None or not user.is_active:
            raise InvalidRequest("User account was not found or is inactive.")
        product = await self.products.get_product_by_sku(sku)
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        current_items = await self.carts.get_cart_by_user_id(user_id)
        if current_items and any(
            item.product.currency != product.currency for item in current_items
        ):
            raise InvalidRequest("A cart cannot contain items in different currencies.")
        item = await self.carts.get_item(user_id, product.id)
        requested = quantity + (item.quantity if item else 0)
        if requested > product.quantity:
            raise InsufficientStock(
                f"Only {product.quantity} unit(s) of '{sku}' are available."
            )
        await self.carts.add_item(user_id, product, quantity)
        await self.session.commit()
        return await self.get_cart(user_id)

    async def remove_item(self, user_id: str, sku: str) -> CartRead:
        await self.carts.remove_item(user_id, sku)
        await self.session.commit()
        return await self.get_cart(user_id)

    async def get_cart(self, user_id: str) -> CartRead:
        items = await self.carts.get_cart_by_user_id(user_id)
        currencies = {item.product.currency for item in items}
        if len(currencies) > 1:
            raise InvalidRequest("A cart cannot contain items in different currencies.")
        lines = [
            CartItemRead(
                sku=item.product.sku,
                name=item.product.name,
                quantity=item.quantity,
                unit_price=item.product.price,
                line_total=item.product.price * item.quantity,
            )
            for item in items
        ]
        total = sum((line.line_total for line in lines), Decimal("0.00"))
        return CartRead(
            user_id=user_id,
            items=lines,
            total=total,
            currency=next(iter(currencies), "INR"),
        )
