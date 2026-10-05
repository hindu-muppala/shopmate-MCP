from collections.abc import AsyncIterator
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


def normalize_database_url(database_url: str) -> tuple[str, dict[str, str]]:
    parts = urlsplit(database_url)
    scheme = parts.scheme
    if scheme == "postgres":
        scheme = "postgresql"
    if scheme == "postgresql":
        scheme = "postgresql+asyncpg"

    user_info, separator, host_port = parts.netloc.rpartition("@")
    if separator:
        username, password_separator, password = user_info.partition(":")
        user_info = quote(unquote(username), safe="")
        if password_separator:
            user_info += ":" + quote(unquote(password), safe="")
        netloc = f"{user_info}@{host_port}"
    else:
        netloc = parts.netloc

    query_items = parse_qsl(parts.query, keep_blank_values=True)
    ssl_modes = {
        value.lower()
        for key, value in query_items
        if key.lower() == "sslmode"
    }
    query_items = [
        (key, value) for key, value in query_items if key.lower() != "sslmode"
    ]
    connect_args = {"ssl": "require"} if ssl_modes else {}
    normalized = urlunsplit(
        (
            scheme,
            netloc,
            parts.path,
            urlencode(query_items),
            parts.fragment,
        )
    )
    return normalized, connect_args


database_url, database_connect_args = normalize_database_url(settings.database_url)
engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=database_connect_args,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
