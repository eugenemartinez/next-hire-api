from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class AppException(Exception):
    """
    Base class for application-specific exceptions.
    Allows for a consistent way to handle errors with a status code and detail.
    """
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        super().__init__(detail)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"


class NotFoundError(AppException):
    """Custom exception for 404 Not Found errors."""
    def __init__(self, detail: Any = "Resource not found", headers: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=404, detail=detail, headers=headers)


class ForbiddenError(AppException):
    """Custom exception for 403 Forbidden errors."""
    def __init__(self, detail: Any = "Operation not permitted", headers: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=403, detail=detail, headers=headers)


class UnprocessableEntityError(AppException):
    """
    Custom exception for 422 Unprocessable Entity errors.
    Typically used when the request is well-formed but contains semantic errors
    that prevent processing (e.g., business rule violation not caught by Pydantic).
    """
    def __init__(self, detail: Any = "Unprocessable entity", headers: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=422, detail=detail, headers=headers)

class BadRequestError(AppException):
    """Custom exception for 400 Bad Request errors."""
    def __init__(self, detail: Any = "Bad request", headers: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=400, detail=detail, headers=headers)

class RowLimitExceededError(HTTPException):
    def __init__(self, detail: str = "The maximum number of records has been reached."):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

# You can add more specific exceptions as needed, e.g.:
# class AuthenticationError(AppException):
#     def __init__(self, detail: Any = "Authentication failed", headers: Optional[Dict[str, Any]] = None):
#         super().__init__(status_code=401, detail=detail, headers=headers)
