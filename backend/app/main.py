import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session as DB
from .db import get_db
from .schemas import Message, ErrorOut
from .routers import auth, projects, applications, moderation, reports

app = FastAPI(
    responses={
        code: {"model": ErrorOut} for code in [401, 403, 404, 409, 422, 429, 503]
    },
    title="МАИ.Команда REST API",
    version="2.0.0",
    description="MVP. Отдельный REST API; тестовые данные явно отмечены.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Проверьте заполнение полей",
            "errors": [
                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                for e in error.errors()
            ],
        },
    )


@app.exception_handler(IntegrityError)
async def conflict(request, error):
    return JSONResponse(
        status_code=409,
        content={"detail": "Запись уже существует или связана с другими данными"},
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, error):
    return JSONResponse(
        status_code=503,
        content={"detail": "Хранилище временно недоступно. Повторите запрос позже."},
    )


@app.middleware("http")
async def headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health", response_model=Message)
def health(db: DB = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"detail": "ok"}


for module in (auth, projects, applications, moderation, reports):
    app.include_router(module.router)
