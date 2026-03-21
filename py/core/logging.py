import json
import logging
import time
from typing import Any

from fastapi import Request
from starlette.responses import Response

SENSITIVE_KEYS = {"password", "token", "access_token", "authorization", "secret", "jwt"}
MAX_LOG_BODY_LENGTH = 2000


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _sanitize_log_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                sanitized[key] = "***"
            else:
                sanitized[key] = _sanitize_log_value(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_log_value(item) for item in value]
    return value


def _truncate_log_text(value: str) -> str:
    if len(value) <= MAX_LOG_BODY_LENGTH:
        return value
    return value[:MAX_LOG_BODY_LENGTH] + "...<truncated>"


def _format_log_payload(value: Any) -> str:
    try:
        return _truncate_log_text(json.dumps(_sanitize_log_value(value), ensure_ascii=False))
    except Exception:
        return _truncate_log_text(str(value))


def _decode_request_body(body: bytes) -> Any:
    if not body:
        return ""
    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def register_request_logging(app) -> None:
    logger = logging.getLogger("py.http")

    @app.middleware("http")
    async def log_http_requests(request: Request, call_next):
        start = time.perf_counter()
        client = request.client.host if request.client else "unknown"
        query_params = dict(request.query_params)
        request_body = await request.body()
        request_payload = _decode_request_body(request_body)

        async def receive():
            return {"type": "http.request", "body": request_body, "more_body": False}

        request = Request(request.scope, receive)

        logger.info(
            "HTTP request client=%s method=%s path=%s query=%s body=%s",
            client,
            request.method,
            request.url.path,
            _format_log_payload(query_params),
            _format_log_payload(request_payload),
        )

        try:
            response = await call_next(request)
        except Exception:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "HTTP request failed client=%s method=%s path=%s latency_ms=%s",
                client,
                request.method,
                request.url.path,
                latency_ms,
            )
            raise

        response_body = b""
        is_streaming = response.headers.get("content-type", "").startswith("text/event-stream")
        if not is_streaming:
            async for chunk in response.body_iterator:
                response_body += chunk
            response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=response.background,
            )

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "HTTP response client=%s method=%s path=%s status=%s latency_ms=%s body=%s",
            client,
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            "<streaming-response>" if is_streaming else _format_log_payload(_decode_request_body(response_body)),
        )
        return response
