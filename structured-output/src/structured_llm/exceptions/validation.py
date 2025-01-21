from typing import Optional
from pydantic import ValidationError

class ValidationRetryError(Exception):
    def __init__(
        self,
        message: str,
        last_error: Optional[ValidationError] = None
    ):
        super().__init__(message)
        self.last_error = last_error 