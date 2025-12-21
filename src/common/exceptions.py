from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

class OAuthException(Exception):
    def __init__(
        self,
        error: str,
        description: str | None = None,
        status_code: int = 400,
        headers: dict | None = None,
    ):
        self.error = error
        self.description = description
        self.status_code = status_code
        self.headers = headers or {}

class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        headers: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code


def attach_exception_handlers(app: FastAPI):

    @app.exception_handler(OAuthException)
    async def oauth_exception_handler(request: Request, exc: OAuthException):
        body = {"error": exc.error}

        if exc.description:
            body["error_description"] = exc.description

        return JSONResponse(
            status_code=exc.status_code,
            content=body,
            headers=exc.headers,
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": False,
                "message": exc.message,
            },
            headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "status": False,
                "message": "Internal server error",
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        messages = []

        for err in exc.errors():
            loc = err.get("loc", [])
            err_type = err.get("type", "")

            where = loc[0] if len(loc) > 0 else "request"
            field = loc[-1] if len(loc) > 1 else "field"

            if err_type == "missing":
                messages.append(f"missing field '{field}' in {where}")
            else:
                messages.append(f"invalid field '{field}' in {where}")

        # remove duplicates while preserving order
        messages = list(dict.fromkeys(messages))

        return JSONResponse(
            status_code=400,
            content={
                "status": False,
                "message": "Invalid request: " + ", ".join(messages),
            },
        )
