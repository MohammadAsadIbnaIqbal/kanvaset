from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.project import (
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    ProjectMemberAdd,
    ProjectMemberOut,
)
from backend.app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/workspace/{workspace_id}", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    workspace_id: str,
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.create_project(
        db, workspace_id=workspace_id, user_id=current_user.id, project_in=project_in
    )
    return ProjectOut(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        description=project.description,
        revision=project.revision,
        created_at=project.created_at,
        updated_at=project.updated_at,
        role="OWNER",
        tasks_count=0,
    )

@router.get("/workspace/{workspace_id}", response_model=List[ProjectOut])
async def list_workspace_projects(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects = await project_service.get_workspace_projects(db, workspace_id=workspace_id, user_id=current_user.id)
    return [ProjectOut(**proj) for proj in projects]

@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proj_dict = await project_service.get_project(
        db, project_id=project_id, user_id=current_user.id
    )
    return ProjectOut(**proj_dict)

@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.update_project(
        db, project_id=project_id, user_id=current_user.id, project_in=project_in
    )
    proj_dict = await project_service.get_project(db, project_id=project.id, user_id=current_user.id)
    return ProjectOut(**proj_dict)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await project_service.delete_project(db, project_id=project_id, user_id=current_user.id)

@router.post("/{project_id}/members", response_model=ProjectMemberOut)
async def add_project_member(
    project_id: str,
    member_in: ProjectMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member, target_user = await project_service.add_project_member(
        db=db,
        project_id=project_id,
        user_query=member_in.user_email_or_username,
        role=member_in.role,
        current_user_id=current_user.id,
    )
    return ProjectMemberOut(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        username=target_user.username,
        email=target_user.email,
        role=member.role,
        created_at=member.created_at,
    )

@router.get("/{project_id}/members", response_model=List[ProjectMemberOut])
async def list_project_members(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await project_service.get_project_members(db, project_id=project_id, user_id=current_user.id)

@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await project_service.remove_project_member(db, project_id=project_id, member_user_id=user_id, current_user_id=current_user.id)
