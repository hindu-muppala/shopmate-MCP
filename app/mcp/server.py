import json
from decimal import Decimal

from fastmcp import FastMCP

from app.auth.dependencies import get_authenticated_mcp_user_id
from app.database import SessionFactory
from app.dependencies import create_services
from app.exceptions import ShopMateError
from app.schemas.catalog import ProductSearchInput

mcp = FastMCP("ShopMate E-commerce MCP")


def _json(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, list):
        value = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in value
        ]
    return json.dumps(value, default=str)


def _error_message(error: Exception) -> str:
    return _json({"error": str(error)})


@mcp.tool(
    description="Search the product catalog by text and optional maximum price. "
    "Returns matching products with prices, category, and stock availability."
)
async def search_products(query: str, max_price: float | None = None) -> str:
    try:
        request = ProductSearchInput(
            query=query or None,
            max_price=Decimal(str(max_price)) if max_price is not None else None,
        )
        async with SessionFactory() as session:
            products = await create_services(session).catalog.search(request)
            return _json(products)
    except (ShopMateError, ValueError) as exc:
        return _error_message(exc)


@mcp.tool(
    description="Add a positive quantity of a product SKU to the authenticated "
    "user's cart. The requested quantity is checked against current stock."
)
async def add_to_cart(user_id: str, sku: str, quantity: int) -> str:
    try:
        authenticated_user_id = get_authenticated_mcp_user_id(user_id)
        async with SessionFactory() as session:
            cart = await create_services(session).cart.add_to_cart(
                authenticated_user_id, sku, quantity
            )
            return _json(cart)
    except (ShopMateError, ValueError) as exc:
        return _error_message(exc)


@mcp.tool(
    description="Return the authenticated user's order status for the supplied "
    "order ID. Orders belonging to other users are not disclosed."
)
async def get_order_status(order_id: str) -> str:
    try:
        user_id = get_authenticated_mcp_user_id()
        async with SessionFactory() as session:
            order = await create_services(session).orders.get_order_status(
                order_id, user_id
            )
            return _json(order)
    except (ShopMateError, ValueError) as exc:
        return _error_message(exc)


@mcp.tool(
    description="Validate and submit the authenticated user's current cart as a "
    "pending order. Stock is decremented atomically only if checkout succeeds."
)
async def process_checkout(user_id: str) -> str:
    try:
        authenticated_user_id = get_authenticated_mcp_user_id(user_id)
        async with SessionFactory() as session:
            result = await create_services(session).checkout.process_checkout(
                authenticated_user_id
            )
            return _json(result)
    except (ShopMateError, ValueError) as exc:
        return _error_message(exc)


@mcp.tool(
    description="Check current available stock for a product SKU and whether it "
    "meets the requested quantity."
)
async def check_inventory(sku: str, quantity: int = 1) -> str:
    try:
        if quantity < 1:
            raise ValueError("Quantity must be greater than zero.")
        async with SessionFactory() as session:
            inventory = await create_services(session).inventory.check_stock_level(
                sku, quantity
            )
            return _json(inventory)
    except (ShopMateError, ValueError) as exc:
        return _error_message(exc)


@mcp.resource("resource://catalog/categories")
async def catalog_categories() -> str:
    """List the current product category taxonomy."""
    async with SessionFactory() as session:
        return _json(await create_services(session).catalog.get_categories())


@mcp.resource("resource://policies/returns")
def return_policy() -> str:
    """Explain the store's current return policy."""
    return (
        "Items can be returned within 30 days if unused and in original packaging. "
        "Final-sale items are excluded."
    )
