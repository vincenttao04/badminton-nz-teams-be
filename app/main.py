from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import auth, slots, teams, tournaments
from app.db import get_engine


def create_app() -> FastAPI:
    app = FastAPI(title="Badminton NZ Team Events API")
    app.include_router(auth.router, prefix="/v1")
    app.include_router(teams.router, prefix="/v1")
    app.include_router(tournaments.router, prefix="/v1")
    app.include_router(slots.router, prefix="/v1")

    # Backend liveness check
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Database readiness check
    @app.get("/health/ready")
    def readiness() -> dict[str, str]:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=503, detail="database unavailable") from exc
        return {"status": "ready"}

    return app


app = create_app()
