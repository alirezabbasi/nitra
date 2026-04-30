import httpx
from fastapi import Request, Response

from app.core.legacy_bridge import LEGACY_APP


def _legacy_fallback_path(path: str) -> str | None:
    if path.startswith("/api/v1/charting/"):
        return path.replace("/api/v1/charting/", "/api/v1/", 1)
    return None


async def proxy_to_legacy(request: Request) -> Response:
    transport = httpx.ASGITransport(app=LEGACY_APP)
    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://legacy") as client:
        primary_path = str(request.url.path) + (f"?{request.url.query}" if request.url.query else "")
        proxied = await client.request(
            method=request.method,
            url=primary_path,
            content=body,
            headers=headers,
        )
        if proxied.status_code == 404:
            fallback_path = _legacy_fallback_path(str(request.url.path))
            if fallback_path:
                fallback_url = fallback_path + (f"?{request.url.query}" if request.url.query else "")
                proxied = await client.request(
                    method=request.method,
                    url=fallback_url,
                    content=body,
                    headers=headers,
                )

    passthrough_headers = {
        key: value
        for key, value in proxied.headers.items()
        if key.lower() not in {"content-length", "transfer-encoding", "connection"}
    }
    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        media_type=proxied.headers.get("content-type"),
        headers=passthrough_headers,
    )
