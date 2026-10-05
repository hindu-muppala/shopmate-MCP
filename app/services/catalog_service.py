import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.category import Category
from app.repositories.product_repository import ProductRepository
from app.schemas.catalog import ProductResult, ProductSearchInput

_catalog_cache: dict[tuple[object, ...], tuple[float, list[ProductResult]]] = {}


class CatalogService:
    def __init__(
        self,
        products: ProductRepository,
        session: AsyncSession,
        cache_ttl: int | None = None,
    ) -> None:
        self.products = products
        self.session = session
        self.cache_ttl = (
            settings.catalog_cache_ttl_seconds if cache_ttl is None else cache_ttl
        )
        self._cache = _catalog_cache

    async def search(self, request: ProductSearchInput) -> list[ProductResult]:
        return await self.search_products(
            request.query,
            max_price=request.max_price,
            min_price=request.min_price,
            category=request.category,
            color=request.color,
            size=request.size,
            limit=request.limit,
        )

    async def search_products(
        self,
        query: str | None = None,
        max_price: Decimal | None = None,
        min_price: Decimal | None = None,
        category: str | None = None,
        color: str | None = None,
        size: str | None = None,
        limit: int = 10,
    ) -> list[ProductResult]:
        cache_key = (query, min_price, max_price, category, color, size, limit)
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        expired_keys = [
            key for key, (expires_at, _) in self._cache.items() if expires_at <= now
        ]
        for key in expired_keys:
            del self._cache[key]
        if cached and cached[0] > now:
            return cached[1].copy()

        products = await self.products.search_products(
            query=query,
            min_price=min_price,
            max_price=max_price,
            category=category,
            color=color,
            size=size,
            limit=limit,
        )
        results = [
            ProductResult(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                category=product.category.name if product.category else None,
                price=product.price,
                currency=product.currency,
                available=product.quantity > 0,
                attributes=product.attributes,
            )
            for product in products
        ]
        if self.cache_ttl > 0:
            if len(self._cache) >= 256:
                self._cache.pop(next(iter(self._cache)))
            self._cache[cache_key] = (now + self.cache_ttl, results)
        return results.copy()

    async def get_categories(self) -> list[dict[str, str]]:
        categories = await self.session.scalars(
            select(Category).order_by(Category.name)
        )
        return [{"name": item.name, "slug": item.slug} for item in categories]
