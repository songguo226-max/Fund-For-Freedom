from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.integrations.fund_data.interface import FundNotFound, ProviderError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(FundNotFound)
    async def _not_found(_: Request, exc: FundNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ProviderError)
    async def _provider_error(_: Request, exc: ProviderError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
