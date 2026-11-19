from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.config import Settings
from app.store import UserStore
from app.api import router
from app.security import hash_password

def create_app(
    settings: Settings | None = None,
    store: UserStore | None = None
) -> FastAPI:

    settings = settings or Settings.from_env()
    store = store or UserStore()

    app = FastAPI(
        title="Malaria Screening Authentication Service",
        version="1.0.0"
    )

    app.state.settings = settings
    app.state.store = store

    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ):
        errors = exc.errors()

        if request.url.path.startswith("/api/v1/auth/"):
            for error in errors:
                error.pop("input", None)

        return JSONResponse(
            status_code=422,
            content=jsonable_encoder({"detail": errors})
        )

    if (
        settings.bootstrap_admin_email
        and settings.bootstrap_admin_password
    ):
        email = settings.bootstrap_admin_email.lower()

        if store.get_by_email(email) is None:
            store.add({
                "email": email,
                "full_name": "System Administrator",
                "password_hash": hash_password(
                    settings.bootstrap_admin_password
                ),
                "role": "administrator",
                "status": "active"
            })

    return app