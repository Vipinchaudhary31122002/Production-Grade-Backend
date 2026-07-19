from fastapi import FastAPI

class RouteRegister:

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    def register(self) -> None:
        self._auth()
        self._user()
        
    def _auth(self) -> None:
        from app.modules.auth.router import router
        self._app.include_router(router)
        
    def _user(self) -> None:
        from app.modules.users.router import router
        self._app.include_router(router)