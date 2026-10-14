"""Document the dependency overrides of a FastAPI application into its OpenAPI schema."""

from importlib.metadata import version

from .main import (
    document_dependency_overrides,
    get_dependant_with_overrides,
    get_openapi_with_overrides,
    get_routes_with_overrides,
)

__version__ = version("fastapi-openapi-overrides")

__all__ = [
    "document_dependency_overrides",
    "get_dependant_with_overrides",
    "get_openapi_with_overrides",
    "get_routes_with_overrides",
]
