import json
import logging
from typing import Any

from groq import APIConnectionError, APIStatusError, AsyncGroq

from app.chat_backend.mcp_client import MCPServiceError, ShopMateMCPClient
from app.config import settings

PROTECTED_TOOLS = {"add_to_cart", "process_checkout", "get_order_status"}
MAX_TOOL_ROUNDS = 5
MAX_TOOL_CALLS = 8
MAX_TOOL_RESULT_LENGTH = 16000
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ShopMate, a helpful e-commerce shopping assistant.
Use the available ShopMate tools for live catalog, inventory, cart, and order
information. Do not invent products, prices, stock levels, or order details.
If a tool reports an error, explain it clearly and suggest a reasonable next
step. Only call process_checkout when the user explicitly asks to place or
submit their order; checkout creates a pending order and does not take payment.
Never ask for or expose passwords, API keys, bearer tokens, or another user's
account details. Keep answers concise and focused on shopping."""


class GroqServiceError(Exception):
    """Raised when the Groq API cannot complete the chat request."""


class GroqNotConfiguredError(GroqServiceError):
    """Raised when the server has no Groq API key configured."""


def groq_api_error_message(status_code: int | None) -> str:
    if status_code in (401, 403):
        return (
            "Groq rejected the configured API credentials. Set GROQ_API_KEY to a "
            "valid GroqCloud API key; xAI/Grok keys are not accepted."
        )
    if status_code == 404:
        return (
            "The configured Groq model was not found. Check GROQ_MODEL and use a "
            "model available on your GroqCloud account."
        )
    if status_code == 429:
        return "Groq free-tier rate limit reached. Wait for the limit to reset, then try again."
    if status_code == 400:
        return (
            "Groq rejected the request. Check that GROQ_MODEL supports chat "
            "completions and function calling."
        )
    if status_code is not None:
        return f"Groq returned HTTP {status_code}. Check the Groq service and try again."
    return "Could not connect to GroqCloud. Check network access and try again."


class ShopMateAgent:
    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._llm = AsyncGroq(api_key=api_key)

    async def close(self) -> None:
        await self._llm.close()

    async def respond(
        self,
        history: list[dict[str, str]],
        mcp_client: ShopMateMCPClient,
        *,
        has_access_token: bool,
        user_id: str | None,
    ) -> str:
        try:
            tools, names = self._groq_tools(
                await mcp_client.list_tools(),
                has_access_token=has_access_token,
            )
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *history,
            ]
            tool_call_count = 0

            for _ in range(MAX_TOOL_ROUNDS):
                response = await self._llm.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools or None,
                    tool_choice="auto" if tools else None,
                    temperature=0.2,
                    max_completion_tokens=1024,
                )
                assistant_message = response.choices[0].message
                if not assistant_message.tool_calls:
                    answer = assistant_message.content
                    if not answer:
                        raise GroqServiceError("Groq returned an empty response.")
                    return answer

                messages.append(self._assistant_tool_message(assistant_message))
                for tool_call in assistant_message.tool_calls:
                    tool_call_count += 1
                    if tool_call_count > MAX_TOOL_CALLS:
                        raise GroqServiceError(
                            "The request required too many tool calls."
                        )
                    name = tool_call.function.name
                    if name not in names:
                        tool_result = "Error: the requested tool is not available."
                    else:
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except (json.JSONDecodeError, TypeError):
                            arguments = None
                        if not isinstance(arguments, dict):
                            tool_result = "Error: tool arguments must be a JSON object."
                        else:
                            if name in {"add_to_cart", "process_checkout"}:
                                if user_id is None:
                                    tool_result = (
                                        "Error: the user must connect an authenticated "
                                        "account before using cart or checkout."
                                    )
                                    messages.append(
                                        self._tool_result(
                                            tool_call.id, tool_result
                                        )
                                    )
                                    continue
                                arguments["user_id"] = user_id
                            try:
                                output, is_error = await mcp_client.call_tool(
                                    name, arguments
                                )
                            except MCPServiceError as exc:
                                tool_result = str(exc)
                            else:
                                tool_result = (
                                    f"Error: {output}" if is_error else output
                                )
                    messages.append(self._tool_result(tool_call.id, tool_result))

            raise GroqServiceError("Groq did not finish the response in time.")
        except APIStatusError as exc:
            logger.warning(
                "Groq API request failed: status=%s code=%s message=%s model=%s",
                exc.status_code,
                getattr(exc, "code", None),
                getattr(exc, "message", "No provider error message available."),
                self.model,
            )
            raise GroqServiceError(groq_api_error_message(exc.status_code)) from exc
        except APIConnectionError as exc:
            logger.warning(
                "Groq API connection failed: error=%s model=%s",
                type(exc).__name__,
                self.model,
            )
            raise GroqServiceError(groq_api_error_message(None)) from exc

    @staticmethod
    def _groq_tools(
        mcp_tools: list[Any], *, has_access_token: bool
    ) -> tuple[list[dict[str, Any]], set[str]]:
        tools: list[dict[str, Any]] = []
        names: set[str] = set()
        for tool in mcp_tools:
            name = tool.name
            if name in PROTECTED_TOOLS and not has_access_token:
                continue

            tool_data = tool.model_dump(by_alias=True, exclude_none=True)
            parameters = tool_data.get(
                "inputSchema", tool_data.get("input_schema", {})
            )
            parameters = json.loads(json.dumps(parameters))
            if name in {"add_to_cart", "process_checkout"}:
                parameters.get("properties", {}).pop("user_id", None)
                parameters["required"] = [
                    field
                    for field in parameters.get("required", [])
                    if field != "user_id"
                ]

            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool.description or "",
                        "parameters": parameters
                        or {"type": "object", "properties": {}},
                    },
                }
            )
            names.add(name)
        return tools, names

    @staticmethod
    def _assistant_tool_message(message: Any) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls or []
            ],
        }

    @staticmethod
    def _tool_result(tool_call_id: str, content: str) -> dict[str, str]:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content[:MAX_TOOL_RESULT_LENGTH],
        }


def create_agent() -> ShopMateAgent:
    if not settings.groq_api_key:
        raise GroqNotConfiguredError(
            "Groq is not configured. Set GROQ_API_KEY on the server; xAI/Grok keys are not compatible."
        )
    return ShopMateAgent(settings.groq_api_key, settings.groq_model)