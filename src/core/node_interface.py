from pydantic import BaseModel


class BaseInput(BaseModel):
    """Base class for node inputs."""


class BaseOutput(BaseModel):
    """Base class for node outputs."""
