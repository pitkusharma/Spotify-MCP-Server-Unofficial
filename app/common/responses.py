from typing import Optional, Any
from pydantic import BaseModel


class AppResponse(BaseModel):
    """
    Standardized response model for all application services.

    Attributes:
        status (bool): Indicates whether the operation succeeded.
        message (str): Human-readable success or error message.
        data (Optional[Any]): Optional payload returned by a service.
    """
    status: bool
    message: str
    data: Optional[Any] = None
