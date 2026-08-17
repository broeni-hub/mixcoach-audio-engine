from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    service: str
    version: str
    environment: str


class ErrorResponse(BaseModel):
    detail: str
