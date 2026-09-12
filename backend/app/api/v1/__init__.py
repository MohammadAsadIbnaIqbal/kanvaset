from fastapi import APIRouter
from backend.app.api.v1 import auth, boards, workspaces, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(boards.router)
api_router.include_router(ws.router)
