# FastAPI OpenAPI Overrides

Document the dependency overrides of a [FastAPI](https://fastapi.tiangolo.com)
application into its OpenAPI schema.

## Why?

FastAPI lets you replace a dependency with another one using
`app.dependency_overrides`. Although designed for testing, this mechanism
is also useful for reusable routers: each application can provide its own
implementation of a dependency, such as authentication.

At runtime, FastAPI uses the overridden dependency to process requests,
including reading its parameters and checking its security requirements.
However, the OpenAPI schema still documents the original dependency.
As a result, the API documentation does not reflect the actual behavior.

This library fixes this by generating the OpenAPI schema using the
overridden dependencies.

A fix was [proposed upstream](https://github.com/fastapi/fastapi/pull/5452)
but rejected. This functionality is therefore provided by an extension
module.

## Usage

```python
from fastapi import APIRouter, Depends, FastAPI, Header

from fastapi_openapi_overrides import document_dependency_overrides


def authenticated_user() -> str:
    """Abstract dependency: the application must provide the implementation."""
    raise NotImplementedError()


router = APIRouter()


@router.get("/me")
def read_me(user: str = Depends(authenticated_user)) -> str:
    return user


def header_user(x_user: str = Header()) -> str:
    return x_user


app = FastAPI()
app.include_router(router)
app.dependency_overrides[authenticated_user] = header_user
document_dependency_overrides(app)

app.openapi()["paths"]["/me"]["get"]["parameters"]
#> [{'name': 'x-user', 'in': 'header', 'required': True, 'schema': {'type': 'string', 'title': 'X-User'}}]
```

Without `document_dependency_overrides(app)`, the `x-user` header would not be
documented, while it's required by the requests.

`document_dependency_overrides()` replaces the `openapi()` method of the app, as
explained in the FastAPI documentation about
[extending OpenAPI](https://fastapi.tiangolo.com/how-to/extending-openapi/). As
with the original method, the schema is generated once and cached into
`app.openapi_schema`: reset it to `None` to regenerate the schema if the
dependency overrides are changed afterwards.

If you already generate the schema yourself, the lower level functions can be
used:

* `get_openapi_with_overrides(app)`: generate the OpenAPI schema of the app with
  the same arguments as `FastAPI.openapi()`;
* `get_routes_with_overrides(routes)`: return the routes to give to
  `fastapi.openapi.utils.get_openapi()`;
* `get_dependant_with_overrides(dependant, dependency_overrides)`: return a copy
  of a dependant where the overridden dependencies are replaced.

The routes and the dependants of the application are never modified.

## Compatibility

FastAPI >= 0.138.

## Development

```bash
uv run --group test pytest
uv run --group typing mypy src
pre-commit run --all-files
```

## Release

The version of the package is computed from the git tags (hatch-vcs) and the
changelog is built from the news fragments (towncrier).

* Each change worth mentioning into the changelog comes with a news fragment
  into the `news` directory: `news/<issue number>.<type>`, or
  `news/+<name>.<type>` for a change without issue, where `<type>` is one of
  `feature`, `bugfix`, `doc`, `removal` or `misc`.
* To release a new version, run the `release` workflow from the GitHub "Actions"
  tab and choose the part of the version to increase (`patch`, `minor` or
  `major`). Once the run is approved (required reviewers of the
  `release-approval` environment), the workflow updates `HISTORY.rst`, tags the
  release, publishes the package to PyPI and creates the GitHub release.
