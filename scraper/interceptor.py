import json
import pathlib

DISCOVERY_LOG = pathlib.Path("data/api_discovery.jsonl")


async def attach_interceptor(page, log_path: pathlib.Path = DISCOVERY_LOG) -> None:
    log_path.parent.mkdir(exist_ok=True)

    async def on_response(response):
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            return
        try:
            body = await response.json()
        except Exception:
            return
        entry = {
            "url": response.url,
            "status": response.status,
            "request_headers": dict(response.request.headers),
            "body": body,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    page.on("response", on_response)
