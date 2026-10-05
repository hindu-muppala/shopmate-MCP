# ShopMate MCP

Async e-commerce API and MCP server built with FastAPI, FastMCP, SQLAlchemy
asyncio, PostgreSQL, Pydantic v2, and JWT bearer authentication.

## Configuration

Set these environment variables before starting the application:

| Variable | Purpose |
| --- | --- |
| `SHOPMATE_DATABASE_URL` | PostgreSQL async URL, e.g. `postgresql+asyncpg://user:password@localhost:5432/shopmate` |
| `SHOPMATE_JWT_SECRET` | Secret used to sign access tokens |
| `SHOPMATE_SECRET_KEY` | Application secret key |
| `SHOPMATE_JWT_ALGORITHM` | JWT algorithm (default `HS256`) |
| `SHOPMATE_ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime (default `30`) |
| `GROQ_API_KEY` (or existing `GROK_API_KEY`) | API key setting used by the Groq chat backend |
| `GROQ_MODEL` | Optional Groq model name (default `openai/gpt-oss-20b`) |
| `MCP_URL` | Optional MCP endpoint (default `http://127.0.0.1:8000/mcp`) |

The built-in secret values are development placeholders. Always set strong,
private values outside local development. The database schema must be created
or migrated before serving requests; production deployments should use
versioned database migrations rather than `metadata.create_all`. PostgreSQL
URLs are normalized to the asyncpg driver used by the application, credentials
are URL-encoded, and an `sslmode` URL option is translated to asyncpg SSL.

## Run

```powershell
uv sync --no-install-project
$env:SHOPMATE_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/shopmate"
$env:SHOPMATE_JWT_SECRET = "replace-with-a-long-random-secret"
$env:SHOPMATE_SECRET_KEY = "replace-with-another-long-random-secret"
$env:GROQ_API_KEY = "your-groqcloud-api-key"
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The REST API is served at `/api`, health checks at `/health`, and the
Streamable HTTP MCP endpoint at `/mcp`. Authenticated REST calls and user-scoped
MCP tools require a bearer token whose subject is the user's database ID.
`app.auth.jwt.create_access_token` creates signed access tokens for an
authenticated user.

The browser storefront is available at `http://127.0.0.1:8000/` when the server
is running; its HTML, CSS, and JavaScript live in `app/frontend/`. It can browse
and filter products, check inventory, and—after a
valid bearer token is supplied—manage the cart, check out, and view order
history. There is no sign-in endpoint; the access token must come from your
development or authentication setup. The page keeps the token in memory only
and clears it when refreshed.

The storefront's ShopMate assistant sends chat messages to `/api/chat`. The
server-side chat backend uses GroqCloud's Python SDK and chat-completions API
with the existing MCP tools for live catalog, inventory, cart, and order data.
The default `openai/gpt-oss-20b` model supports function calling and is
available to the configured GroqCloud key. The backend accepts either `GROQ_API_KEY` or the existing
`GROK_API_KEY` setting and reads the value server-side. Never put the key in
browser code.
Protected cart and order tools require the user's bearer token. The assistant
only checks out when explicitly asked, and checkout creates a pending order
without taking payment.

If chat fails, the UI reports whether GroqCloud rejected the credentials,
could not find the configured model, or reached a free-tier rate limit. Set
`GROQ_MODEL` to a model enabled for your GroqCloud account if necessary, then
restart the server.

The MCP server exposes catalog search, inventory checks, cart updates,
checkout validation, order status, catalog categories, and the return-policy
resource. Checkout creates a pending order after recalculating its total from
current database prices; it does not create a payment-provider session.