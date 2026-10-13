from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts
from starlette.routing import BaseRoute

DependencyOverrides = Mapping[Callable[..., Any], Callable[..., Any]]


def _get_oauth_scopes(dependant: Dependant) -> list[str]:
    """Return the OAuth scopes required by the dependant and its parents."""
    scopes = list(dependant.parent_oauth_scopes or [])
    for scope in dependant.own_oauth_scopes or []:
        if scope not in scopes:
            scopes.append(scope)
    return scopes


def get_dependant_with_overrides(
    dependant: Dependant, dependency_overrides: DependencyOverrides
) -> Dependant:
    """Return a copy of the dependant where the overridden dependencies are replaced
    recursively
    """
    dependencies = []
    for sub_dependant in dependant.dependencies:
        call = sub_dependant.call
        if call is not None and call in dependency_overrides:
            sub_dependant = get_dependant(
                path=sub_dependant.path or "",
                call=dependency_overrides[call],
                name=sub_dependant.name,
                parent_oauth_scopes=_get_oauth_scopes(sub_dependant),
                scope=sub_dependant.scope,
            )
        dependencies.append(
            get_dependant_with_overrides(sub_dependant, dependency_overrides)
        )
    return dataclasses.replace(dependant, dependencies=dependencies)


@dataclasses.dataclass(frozen=True)
class _RouteContextWithOverrides(RouteContext):
    """A route context exposing the dependant resolved with the overrides."""

    dependant: Dependant | None = None


def get_routes_with_overrides(
    routes: Sequence[BaseRoute | RouteContext],
) -> list[RouteContext]:
    """Return the routes to give to `get_openapi()` to document the overrides.

    The routes are not modified: the API routes having dependency overrides are
    replaced by a route context exposing a dependant where the overridden
    dependencies are replaced by their override.
    """
    route_contexts: list[RouteContext] = []
    for route_context in iter_route_contexts(routes):
        provider = getattr(route_context, "dependency_overrides_provider", None)
        dependency_overrides = getattr(provider, "dependency_overrides", None)
        if isinstance(route_context.original_route, APIRoute) and dependency_overrides:
            route_context = _RouteContextWithOverrides(
                route=route_context.route,
                _route_context=route_context._route_context,
                dependant=get_dependant_with_overrides(
                    route_context.dependant, dependency_overrides
                ),
            )
        route_contexts.append(route_context)
    return route_contexts


def get_openapi_with_overrides(app: FastAPI) -> dict[str, Any]:
    """Generate the OpenAPI schema of the app, documenting its dependency overrides."""
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        summary=app.summary,
        description=app.description,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
        routes=get_routes_with_overrides(app.routes),
        webhooks=get_routes_with_overrides(app.webhooks.routes),
        tags=app.openapi_tags,
        servers=app.servers,
        separate_input_output_schemas=app.separate_input_output_schemas,
        external_docs=app.openapi_external_docs,
    )


def document_dependency_overrides(app: FastAPI) -> FastAPI:
    """Make the OpenAPI schema of the app document its dependency overrides."""

    def openapi() -> dict[str, Any]:
        if not app.openapi_schema:
            app.openapi_schema = get_openapi_with_overrides(app)
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]
    return app
