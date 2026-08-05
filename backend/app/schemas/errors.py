from pydantic import BaseModel


class ErrorInjectionResponse(BaseModel):
    status: str
    error_category: str
    message: str

