"""Uniform API error envelope: {"error": {"code": ..., "message": ...}}."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _envelope(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_req: Request, exc: ApiError):
        return _envelope(exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError):
        return _envelope("validation_error", str(exc.errors()[0].get("msg", "invalid")), 422)

    @app.exception_handler(OperationalError)
    async def _db_busy(_req: Request, exc: OperationalError):
        # One writer, so a long import can still out-wait busy_timeout. That is a
        # "try again in a moment", not a server fault, and it must not escape as a
        # bare 500 -- every error leaves through the envelope (see AGENTS.md).
        if "locked" in str(exc.orig).lower() or "busy" in str(exc.orig).lower():
            return _envelope("database_busy", "数据库正忙（可能正在导入词典），请稍后再试", 503)
        return _envelope("database_error", "数据库操作失败", 500)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _envelope(code, str(exc.detail), exc.status_code)
