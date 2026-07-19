from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.router import RouteRegister
from app.core.config import settings
from app.core.database import check_database_connection, dispose_database

class AppFactory:

    @staticmethod
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        check_database_connection()
        yield
        dispose_database()

    @classmethod
    def create(cls) -> FastAPI:
        app = FastAPI(
            title=settings.APP_NAME,
            version="0.1.0",
            debug=bool(settings.DEBUG),
            docs_url="/docs" if bool(settings.DEBUG) else None,
            redoc_url="/redoc" if bool(settings.DEBUG) else None,
            lifespan=cls._lifespan,
        )
        route_registry = RouteRegister(app)
        route_registry.register()
        return app

app: FastAPI = AppFactory.create()

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "server up"}