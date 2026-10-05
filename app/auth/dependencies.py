from fastapi import HTTPException, status
from fastmcp.server.dependencies import get_http_request

from app.auth.jwt import decode_access_token
from app.models.user import User


def get_authenticated_mcp_user_id(expected_user_id: str | None = None) -> str:
    request = get_http_request()
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = str(decode_access_token(token)["sub"])
    if expected_user_id is not None and subject != expected_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own account.",
        )
    return subject


def get_user_context(user: User) -> dict[str, str | bool]:
    return {"user_id": user.id, "email": user.email, "is_active": user.is_active}
