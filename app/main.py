from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Badminton NZ Team Events API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
