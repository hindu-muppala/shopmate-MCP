from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth.jwt import get_current_user
from app.auth.jwt import decode_access_token
from app.chat_backend.llm_agent import (
    GroqNotConfiguredError,
    GroqServiceError,
    create_agent,
)
from app.chat_backend.mcp_client import MCPServiceError, ShopMateMCPClient
from app.config import settings
from app.database import engine
from app.dependencies import Services, get_services
from app.exceptions import (
    CartNotFound,
    InsufficientStock,
    InvalidRequest,
    InvalidOrderTransition,
    OrderNotFound,
    ProductNotFound,
    ShopMateError,
)
from app.mcp.server import mcp
from app.models.user import User
from app.schemas.cart import CartRead, CartUpdate
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.catalog import ProductResult, ProductSearchInput
from app.schemas.checkout import CheckoutRead
from app.schemas.order import OrderRead

logger = logging.getLogger(__name__)

mcp_app = mcp.http_app(path="/", transport="streamable-http", stateless_http=True)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp_app.router.lifespan_context(mcp_app):
        yield
    await engine.dispose()


app = FastAPI(
    title="ShopMate E-commerce API",
    description="E-commerce API and MCP server for AI agents.",
    lifespan=lifespan,
)


@app.exception_handler(ShopMateError)
async def handle_shopmate_error(_, exc: ShopMateError) -> JSONResponse:
    status_code = status.HTTP_404_NOT_FOUND
    if isinstance(exc, (InsufficientStock, InvalidOrderTransition)):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, InvalidRequest):
        status_code = status.HTTP_400_BAD_REQUEST
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> ChatResponse:
    token: str | None = None
    user_id: str | None = None
    if authorization:
        scheme, _, supplied_token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not supplied_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Use a valid bearer access token.",
            )
        token = supplied_token
        user_id = str(decode_access_token(token)["sub"])

    agent = None
    try:
        agent = create_agent()
        async with ShopMateMCPClient(settings.mcp_url, token) as mcp_client:
            reply = await agent.respond(
                [message.model_dump() for message in request.messages],
                mcp_client,
                has_access_token=token is not None,
                user_id=user_id,
            )
        return ChatResponse(reply=reply)
    except GroqNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GroqServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except MCPServiceError as exc:
        logger.exception("ShopMate MCP chat request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to the ShopMate MCP service.",
        ) from exc
    finally:
        if agent is not None:
            await agent.close()


@app.get("/api/catalog/products", response_model=list[ProductResult])
async def search_catalog(
    services: Annotated[Services, Depends(get_services)],
    query: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    category: str | None = None,
) -> list[ProductResult]:
    search = ProductSearchInput(
        query=query,
        min_price=Decimal(str(min_price)) if min_price is not None else None,
        max_price=Decimal(str(max_price)) if max_price is not None else None,
        category=category,
    )
    return await services.catalog.search(search)


@app.get("/api/catalog/categories")
async def catalog_categories(
    services: Annotated[Services, Depends(get_services)],
) -> list[dict[str, str]]:
    return await services.catalog.get_categories()


@app.get("/api/cart", response_model=CartRead)
async def get_cart(
    current_user: Annotated[User, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> CartRead:
    return await services.cart.get_cart(current_user.id)


@app.post("/api/cart/items", response_model=CartRead)
async def add_cart_item(
    item: CartUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> CartRead:
    return await services.cart.add_to_cart(current_user.id, item.sku, item.quantity)


@app.delete("/api/cart/items/{sku}", response_model=CartRead)
async def remove_cart_item(
    sku: str,
    current_user: Annotated[User, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> CartRead:
    return await services.cart.remove_item(current_user.id, sku)


@app.post("/api/checkout", response_model=CheckoutRead)
async def process_checkout(
    current_user: Annotated[User, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> CheckoutRead:
    return await services.checkout.process_checkout(current_user.id)


@app.get("/api/orders", response_model=list[OrderRead])
async def order_history(
    current_user: Annotated[User, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> list[OrderRead]:
    return await services.orders.get_order_history(current_user.id)


@app.get("/api/orders/{order_id}", response_model=OrderRead)
async def order_status(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> OrderRead:
    return await services.orders.get_order_status(order_id, current_user.id)


@app.get("/api/inventory/{sku}")
async def check_inventory(
    sku: str,
    services: Annotated[Services, Depends(get_services)],
    quantity: int = Query(default=1, ge=1),
) -> dict[str, object]:
    return await services.inventory.check_stock_level(sku, quantity)


app.mount("/mcp", mcp_app)


@app.get("/", include_in_schema=False)
async def frontend() -> FileResponse:
    return FileResponse(Path(__file__).parent / "frontend" / "index.html")


app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "frontend"),
    name="static",
)
