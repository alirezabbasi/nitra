import httpx
from fastapi import Request, Response

from app.core.legacy_bridge import LEGACY_APP


async def proxy_to_legacy(request: Request) -> Response:
    transport = httpx.ASGITransport(app=LEGACY_APP)
    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://legacy") as client:
        proxied = await client.request(
            method=request.method,
            url=str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
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
