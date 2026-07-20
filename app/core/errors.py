from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        fields: list[dict[str, str]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields


def _error_body(
    *,
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return {"success": False, "error": error}


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            code=exc.code,
            message=exc.message,
            fields=exc.fields,
        ),
    )


async def api_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    if not request.url.path.startswith("/api/v1/"):
        return await request_validation_exception_handler(request, exc)

    fields: list[dict[str, str]] = []
    for error in exc.errors():
        location = error.get("loc", ())
        field = str(location[-1]) if location else "body"
        if field == "phone_number":
            field = "phoneNumber"
        reason = str(error.get("msg", "입력값이 올바르지 않습니다."))
        reason = reason.removeprefix("Value error, ")
        fields.append({"field": field, "reason": reason})

    return JSONResponse(
        status_code=400,
        content=_error_body(
            code="VALIDATION_ERROR",
            message="입력값을 확인해 주세요.",
            fields=fields,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, api_validation_error_handler)
