from fastapi import FastAPI

class RouteRegister:

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    def register(self) -> None:
        pass
        
    def _register_cold_email(self) -> None:
        pass