from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories import (
    CartRepository,
    InventoryRepository,
    OrderRepository,
    ProductRepository,
)
from app.services import (
    CartService,
    CatalogService,
    CheckoutService,
    InventoryService,
    OrderService,
)


@dataclass(slots=True)
class Services:
    catalog: CatalogService
    cart: CartService
    checkout: CheckoutService
    inventory: InventoryService
    orders: OrderService


def create_services(session: AsyncSession) -> Services:
    products = ProductRepository(session)
    carts = CartRepository(session)
    orders = OrderRepository(session)
    inventory = InventoryRepository(session)
    inventory_service = InventoryService(inventory)
    return Services(
        catalog=CatalogService(products, session),
        cart=CartService(session, carts, products),
        inventory=inventory_service,
        checkout=CheckoutService(session, carts, orders, inventory_service),
        orders=OrderService(orders),
    )


async def get_services(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Services:
    return create_services(session)
