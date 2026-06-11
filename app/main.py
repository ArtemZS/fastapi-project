from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from loguru import logger
from uuid import uuid4
from fastapi.responses import JSONResponse

from app.routers import categories, products, users, reviews, cart_items, orders


# Создаём приложение FastAPI
app = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)

#? Логирование с помощью Loguru
logger.add("info.log", format="Log: [{extra[log_id]}:{time} - {level} - {message}]", level="INFO", enqueue = True)

# Подключаем маршруты
app.include_router(categories.router)
app.include_router(categories.router_v2)
app.include_router(products.router)
app.include_router(products.router_v2)
app.include_router(users.router)
app.include_router(users.router_v2)
app.include_router(reviews.router)
app.include_router(reviews.router_v2)
app.include_router(cart_items.router)
app.include_router(orders.router)


app.mount("/media", StaticFiles(directory="media"), name="media")


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    log_id = str(uuid4())
    with logger.contextualize(log_id=log_id):
        try:
            response = await call_next(request)
            if response.status_code in [401, 402, 403, 404]:
                logger.warning(f"Request to {request.url.path} failed")
            else:
                logger.info(f"Successfully accessed {request.url.path}")
        except Exception as ex:
            logger.exception(f"Request to {request.url.path} failed: {ex}")
            response = JSONResponse(content={"success": False}, status_code=500)
        return response


# Корневой эндпоинт для проверки
@app.get("/")
async def root():
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    #? raise Exception("Тестовая ошибка для проверки логирования") #? Искусственно вызываем ошибку для проверки логирования
    
    return {"message": "Добро пожаловать в API интернет-магазина!"}
