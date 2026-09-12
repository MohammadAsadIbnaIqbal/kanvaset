import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.v1 import api_router
from backend.app.api.v1.ws import router as ws_router
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.core.redis import redis_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kanvaset.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Kanvaset Backend...")
    await redis_service.connect()
    
    # In development / SQLite mode, ensure database tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schemas verified.")

    yield

    # Shutdown
    logger.info("Shutting down Kanvaset Backend...")
    await redis_service.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Real-Time Collaborative Workspace Backend API & WebSockets",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
origins = settings.CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response


# Health and Readiness Probe
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "redis_connected": redis_service.is_connected,
    }


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also expose direct /ws path so frontends can connect to /ws/boards/{id} directly
app.include_router(ws_router)
