from fastapi import Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy


DEPRECATION_SUNSET = "Fri, 31 Jul 2026 00:00:00 GMT"


def _with_deprecation_headers(response: Response, replacement: str) -> Response:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = DEPRECATION_SUNSET
    response.headers["Link"] = f'<{replacement}>; rel="successor-version"'
    return response


async def proxy_charting(request: Request) -> Response:
    return await proxy_to_legacy(request)


async def proxy_charting_alias(request: Request, *, replacement: str) -> Response:
    proxied = await proxy_to_legacy(request)
    return _with_deprecation_headers(proxied, replacement)
