from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUDRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get(self, object_id: object) -> ModelT | None:
        return await self.session.get(self.model, object_id)

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self.session.scalars(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result)

    async def create(self, **values: object) -> ModelT:
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
