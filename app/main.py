"""Arranque de la API.

Registra las rutas, abre SQLite al iniciar y traduce los errores de negocio
a JSON. La lógica de facturas vive en los servicios.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import create_session_factory
from app.deps import get_db, get_settings
from app.errors import ApiError
from app.routes.documents import router as documents_router
from app.routes.mock_admin import router as mock_admin_router
from app.schemas.invoice import HealthResponse

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "Sistema", "description": "Estado de la API."},
    {
        "name": "Documentos",
        "description": "Recepción, consulta y notificación de facturas.",
    },
    {
        "name": "Mock sistema administrativo",
        "description": "Simulación local del sistema externo. No es el sistema real de Diosmar.",
    },
]


def _configure_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


def create_app() -> FastAPI:
    settings = Settings()
    _configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        engine, session_factory = create_session_factory(settings.database_url)
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        logger.info(
            "API lista. extraction_mode=%s run_mode=%s ERP no configurado",
            settings.extraction_mode,
            settings.run_mode,
        )
        yield
        engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        summary="MVP de automatización de facturas para la prueba técnica de Diosmar.",
        description=(
            "Recibe un PDF, extrae texto, interpreta y valida los datos. El alta en el ERP y "
            "el correo están pendientes de configurar con el contrato real del ERP. "
            "RUN_MODE=dry evita altas y correos."
        ),
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )
    app.add_exception_handler(ApiError, _api_error_handler)
    app.include_router(documents_router, prefix="/api/documents", tags=["Documentos"])
    app.include_router(
        mock_admin_router,
        prefix="/api/mock/admin",
        tags=["Mock sistema administrativo"],
    )

    @app.get("/health", tags=["Sistema"], response_model=HealthResponse)
    def health(
        db: Session = Depends(get_db),
        current_settings: Settings = Depends(get_settings),
    ):
        db.execute(text("SELECT 1"))
        return HealthResponse(
            status="ok",
            extraction_mode=current_settings.extraction_mode,
            run_mode=current_settings.run_mode,
            notification_mode="simulated",
            database="ok",
        )

    return app


app = create_app()
