from typing import Any

import httpx2
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from mcp.shared.exceptions import MCPError


class MCPServiceError(Exception):
    """Raised when the ShopMate MCP server cannot be reached or used."""


class ShopMateMCPClient:
    def __init__(self, url: str, access_token: str | None = None) -> None:
        headers = (
            {"Authorization": f"Bearer {access_token}"} if access_token else None
        )
        self._client = Client(StreamableHttpTransport(url, headers=headers))

    async def __aenter__(self) -> ShopMateMCPClient:
        try:
            await self._client.__aenter__()
        except (httpx2.HTTPError, MCPError, TimeoutError) as exc:
            raise MCPServiceError(
                "Could not connect to the ShopMate MCP server."
            ) from exc
        return self

    async def __aexit__(
        self, exc_type: Any, exc_value: Any, traceback: Any
    ) -> None:
        await self._client.__aexit__(exc_type, exc_value, traceback)

    async def list_tools(self) -> list[Any]:
        try:
            return await self._client.list_tools()
        except (httpx2.HTTPError, MCPError, TimeoutError) as exc:
            raise MCPServiceError(
                "Could not load tools from the MCP server."
            ) from exc

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> tuple[str, bool]:
        try:
            result = await self._client.call_tool(
                name,
                arguments,
                raise_on_error=False,
            )
        except (httpx2.HTTPError, MCPError, TimeoutError) as exc:
            raise MCPServiceError("The ShopMate MCP tool call failed.") from exc

        text = "\n".join(
            item.text for item in result.content if hasattr(item, "text")
        )
        if not text and result.structured_content is not None:
            text = str(result.structured_content)
        return text[:16000], result.is_error