from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_api_key(x_api_key: str = Header(..., description="API key for authentication")):
    """
    Validates the API key from request headers.

    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


# Alternative dependency for optional auth (useful for health checks)
async def verify_api_key_optional(x_api_key: str = Header(None)):
    if x_api_key and x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key
