"""
HTTP request logging middleware.

Logs all HTTP requests with:
- Unique request ID for tracing
- Method, path, query params
- Status code and latency
- Client IP
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all HTTP requests and responses.
    
    Excludes /health endpoint to reduce noise.
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip logging for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Generate unique trace ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log incoming request
        logger.info(
            "HTTP request received",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params) if request.query_params else {},
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        # Measure execution time
        start_time = time.perf_counter()
        
        # Process request
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # Log response
            logger.info(
                "HTTP request completed",
                extra={
                    "event": "http_response",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
            
            # Add request ID to response headers for client-side tracing
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # Log error
            logger.error(
                f"HTTP request failed: {str(e)}",
                extra={
                    "event": "http_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise
