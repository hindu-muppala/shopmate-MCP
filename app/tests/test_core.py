from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.auth.jwt import create_access_token, decode_access_token
from app.database import normalize_database_url
from app.exceptions import InvalidOrderTransition
from app.models.order import Order, OrderStatus
from app.schemas.catalog import ProductSearchInput
from app.services.catalog_service import CatalogService, _catalog_cache
from app.services.inventory_service import InventoryService
from app.services.order_service import OrderService


def test_database_url_normalizes_async_driver_and_escapes_password() -> None:
    normalized, connect_args = normalize_database_url(
        "postgresql://shopmate:p@ss@db.example.com:5432/shopmate?sslmode=require"
    )

    assert normalized == (
        "postgresql+asyncpg://shopmate:p%40ss@db.example.com:5432/shopmate"
    )
    assert connect_args == {"ssl": "require"}


def test_database_url_preserves_async_driver_and_other_options() -> None:
    normalized, connect_args = normalize_database_url(
        "postgresql+asyncpg://shopmate:p%40ss@db.example.com:5432/shopmate"
        "?prepared_statement_cache_size=0"
    )

    assert normalized.endswith("?prepared_statement_cache_size=0")
    assert normalized.startswith("postgresql+asyncpg://")
    assert connect_args == {}


def test_access_token_round_trip() -> None:
    token = create_access_token("user-123")

    assert decode_access_token(token)["sub"] == "user-123"


def test_invalid_access_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        decode_access_token("not-a-valid-token")

    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_inventory_reports_sufficient_stock() -> None:
    repository = SimpleNamespace(check_stock_level=AsyncMock(return_value=4))
    service = InventoryService(repository)

    result = await service.check_stock_level("sku-1", quantity=3)

    assert result == {
        "sku": "sku-1",
        "requested_quantity": 3,
        "available_quantity": 4,
        "available": True,
    }


@pytest.mark.asyncio
async def test_catalog_search_uses_cache() -> None:
    _catalog_cache.clear()
    products = SimpleNamespace(search_products=AsyncMock(return_value=[]))
    service = CatalogService(products, session=AsyncMock(), cache_ttl=60)
    request = ProductSearchInput(query="boots")

    assert await service.search(request) == []
    assert await service.search(request) == []

    products.search_products.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_status_transition_rejects_shipped_to_paid() -> None:
    repository = SimpleNamespace(
        session=SimpleNamespace(commit=AsyncMock()),
    )
    order = Order(
        id="order-1",
        user_id="user-1",
        status=OrderStatus.SHIPPED,
        total=Decimal("10.00"),
        currency="INR",
        items=[],
    )
    service = OrderService(repository)  # type: ignore[arg-type]

    with pytest.raises(InvalidOrderTransition, match="Cannot change order status"):
        await service.update_status(order, OrderStatus.PAID)

    repository.session.commit.assert_not_awaited()
