import logging
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.redis import redis_service
from backend.app.models.project import Project
from backend.app.models.task import Task, TaskComment
from backend.app.models.history import TaskVersion, Activity
from backend.app.schemas.ws_messages import WSMessage, WSMessageType

logger = logging.getLogger("kanvaset.project_engine")


class ProjectCollaborationEngine:
    @staticmethod
    async def process_operation(
        db: AsyncSession,
        msg: WSMessage,
        user_id: str,
        user_name: str,
        role: str
    ) -> Tuple[Optional[WSMessage], Optional[str]]:
        """
        Validates, applies, and persists a task operation for a project.
        Returns (broadcast_message, error_string).
        """
        if role == "VIEWER":
            return None, "Viewers are not permitted to modify this project."

        if msg.operation_id:
            is_duplicate = await redis_service.check_and_mark_operation(msg.operation_id)
            if is_duplicate:
                p_stmt = select(Project).where(Project.id == msg.project_id)
                p_res = await db.execute(p_stmt)
                p_obj = p_res.scalars().first()
                rev = p_obj.revision if p_obj else 0
                return WSMessage(
                    type=WSMessageType.ACK,
                    project_id=msg.project_id,
                    operation_id=msg.operation_id,
                    server_revision=rev,
                ), None

        project_stmt = select(Project).where(Project.id == msg.project_id).with_for_update()
        res_project = await db.execute(project_stmt)
        project = res_project.scalars().first()
        if not project:
            return None, "Project does not exist."

        project.revision += 1
        new_revision = project.revision

        payload = msg.payload or {}
        target_task_id = msg.task_id or payload.get("id")
        out_payload = dict(payload)

        task = None
        if target_task_id:
            task_stmt = select(Task).where(Task.id == target_task_id)
            res_task = await db.execute(task_stmt)
            task = res_task.scalars().first()

        activity_action = None

        if msg.type == WSMessageType.TASK_CREATED:
            if not target_task_id:
                return None, "Task ID is required for TASK_CREATED."
            
            if task and task.project_id != msg.project_id:
                return None, "Task belongs to another project."

            try:
                if task:
                    task.is_deleted = False
                    task.title = str(payload.get("title", task.title))
                    task.description = str(payload.get("description", task.description or ""))
                    task.status = str(payload.get("status", task.status))
                    task.priority = str(payload.get("priority", task.priority))
                    task.assignee_id = payload.get("assignee_id", task.assignee_id)
                    task.tags = payload.get("tags", task.tags)
                    task.version += 1
                    task.last_modified_by = user_id
                else:
                    task = Task(
                        id=target_task_id,
                        project_id=msg.project_id,
                        title=str(payload.get("title", "New Task")),
                        description=str(payload.get("description", "")),
                        status=str(payload.get("status", "TODO")),
                        priority=str(payload.get("priority", "MEDIUM")),
                        assignee_id=payload.get("assignee_id"),
                        tags=payload.get("tags", []),
                        version=1,
                        is_deleted=False,
                        created_by=user_id,
                        last_modified_by=user_id,
                    )
                    db.add(task)
                
                await db.flush()
                out_payload = task.to_dict()
                activity_action = "TASK_CREATED"
            except (ValueError, TypeError) as e:
                return None, f"Invalid value in payload: {str(e)}"

        elif msg.type == WSMessageType.TASK_UPDATED:
            if not task or task.is_deleted:
                return None, f"Task {target_task_id} not found."
            if task.project_id != msg.project_id:
                return None, "Task belongs to another project."

            try:
                if "title" in payload:
                    task.title = str(payload["title"])
                if "description" in payload:
                    task.description = str(payload["description"])
                if "status" in payload:
                    task.status = str(payload["status"])
                if "priority" in payload:
                    task.priority = str(payload["priority"])
                if "assignee_id" in payload:
                    task.assignee_id = payload["assignee_id"]
                if "tags" in payload:
                    task.tags = payload["tags"]
            except (ValueError, TypeError) as e:
                return None, f"Invalid value in payload: {str(e)}"

            task.version += 1
            task.last_modified_by = user_id
            await db.flush()
            out_payload = task.to_dict()
            activity_action = "TASK_UPDATED"

        elif msg.type == WSMessageType.TASK_DELETED:
            if not task or task.is_deleted:
                return None, f"Task {target_task_id} not found."
            if task.project_id != msg.project_id:
                return None, "Task belongs to another project."

            task.is_deleted = True
            task.version += 1
            task.last_modified_by = user_id
            await db.flush()
            out_payload = {"id": target_task_id, "is_deleted": True}
            activity_action = "TASK_DELETED"
            
        elif msg.type == WSMessageType.TASK_COMMENT_ADDED:
            if not task or task.is_deleted:
                return None, "Task not found."
            comment_content = payload.get("content")
            if not comment_content:
                return None, "Comment content is required."
                
            comment = TaskComment(
                task_id=task.id,
                user_id=user_id,
                content=str(comment_content)
            )
            db.add(comment)
            await db.flush()
            out_payload = {
                "id": comment.id,
                "task_id": task.id,
                "user_id": user_id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat()
            }
            activity_action = "TASK_COMMENT_ADDED"

        # Record Task Version for History
        if task and msg.type in [WSMessageType.TASK_CREATED, WSMessageType.TASK_UPDATED]:
            tv = TaskVersion(
                task_id=task.id,
                user_id=user_id,
                revision=task.version,
                snapshot=task.to_dict()
            )
            db.add(tv)
        
        # Record Activity
        if activity_action:
            act = Activity(
                project_id=msg.project_id,
                user_id=user_id,
                action_type=activity_action,
                entity_id=target_task_id,
                metadata_=out_payload
            )
            db.add(act)
        
        await db.flush()

        broadcast_msg = WSMessage(
            type=msg.type,
            project_id=msg.project_id,
            operation_id=msg.operation_id,
            task_id=target_task_id,
            payload=out_payload,
            client_revision=msg.client_revision,
            server_revision=new_revision,
            user_id=user_id,
            user_name=user_name,
        )
        return broadcast_msg, None


project_engine = ProjectCollaborationEngine()
