import logging
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.redis import redis_service
from backend.app.models.board import Board
from backend.app.models.board_object import BoardObject
from backend.app.models.operation import BoardOperation
from backend.app.schemas.ws_messages import WSMessage, WSMessageType

logger = logging.getLogger("kanvaset.collaboration")


class CollaborationEngine:
    @staticmethod
    async def process_operation(
        db: AsyncSession,
        msg: WSMessage,
        user_id: str,
        user_name: str,
        role: str
    ) -> Tuple[Optional[WSMessage], Optional[str]]:
        """
        Validates, applies, and persists a semantic operation.
        Returns (broadcast_message, error_string).
        """
        # 1. Authorization: VIEWER cannot mutate board
        if role == "VIEWER":
            return None, "Viewers are not permitted to modify this board."

        # 2. Deduplication check
        if msg.operation_id:
            is_duplicate = await redis_service.check_and_mark_operation(msg.operation_id)
            if is_duplicate:
                logger.info("Ignoring duplicate operation %s", msg.operation_id)
                return None, None

        # 3. Load Board and increment monotonic revision
        board_stmt = select(Board).where(Board.id == msg.board_id)
        res_board = await db.execute(board_stmt)
        board = res_board.scalars().first()
        if not board:
            return None, "Board does not exist."

        board.revision += 1
        new_revision = board.revision

        payload = msg.payload or {}
        target_obj_id = msg.object_id or payload.get("id")
        out_payload = dict(payload)

        # 4. Handle operation types
        if msg.type == WSMessageType.OBJECT_CREATED:
            if not target_obj_id:
                return None, "Object ID is required for OBJECT_CREATED."
            
            # Check if object exists
            obj_stmt = select(BoardObject).where(BoardObject.id == target_obj_id)
            res_obj = await db.execute(obj_stmt)
            obj = res_obj.scalars().first()

            if obj:
                # Revive or update if already present
                obj.is_deleted = False
                obj.type = payload.get("type", obj.type)
                obj.x = float(payload.get("x", obj.x))
                obj.y = float(payload.get("y", obj.y))
                obj.width = float(payload.get("width", obj.width))
                obj.height = float(payload.get("height", obj.height))
                obj.rotation = float(payload.get("rotation", obj.rotation))
                obj.z_index = int(payload.get("z_index", obj.z_index))
                obj.color = payload.get("color", obj.color)
                obj.fill = payload.get("fill", obj.fill)
                obj.stroke = payload.get("stroke", obj.stroke)
                obj.stroke_width = float(payload.get("stroke_width", obj.stroke_width))
                obj.text = payload.get("text", obj.text)
                obj.properties = payload.get("properties", obj.properties)
                obj.version += 1
                obj.last_modified_by = user_id
            else:
                obj = BoardObject(
                    id=target_obj_id,
                    board_id=msg.board_id,
                    type=payload.get("type", "rectangle"),
                    x=float(payload.get("x", 0.0)),
                    y=float(payload.get("y", 0.0)),
                    width=float(payload.get("width", 120.0)),
                    height=float(payload.get("height", 80.0)),
                    rotation=float(payload.get("rotation", 0.0)),
                    z_index=int(payload.get("z_index", 0)),
                    color=payload.get("color", "#ffffff"),
                    fill=payload.get("fill", "#ffffff"),
                    stroke=payload.get("stroke", "#000000"),
                    stroke_width=float(payload.get("stroke_width", 1.5)),
                    text=payload.get("text", ""),
                    properties=payload.get("properties", {}),
                    version=1,
                    is_deleted=False,
                    created_by=user_id,
                    last_modified_by=user_id,
                )
                db.add(obj)
            
            await db.flush()
            await db.refresh(obj)
            out_payload = obj.to_dict()

        elif msg.type == WSMessageType.OBJECT_MOVED:
            if not target_obj_id:
                return None, "Object ID required for OBJECT_MOVED."
            
            obj_stmt = select(BoardObject).where(
                BoardObject.id == target_obj_id,
                BoardObject.board_id == msg.board_id
            )
            res_obj = await db.execute(obj_stmt)
            obj = res_obj.scalars().first()
            if not obj or obj.is_deleted:
                return None, f"Object {target_obj_id} not found."

            if "x" in payload:
                obj.x = float(payload["x"])
            if "y" in payload:
                obj.y = float(payload["y"])
            obj.version += 1
            obj.last_modified_by = user_id
            await db.flush()
            out_payload = {"id": obj.id, "x": obj.x, "y": obj.y, "version": obj.version}

        elif msg.type == WSMessageType.OBJECT_RESIZED:
            if not target_obj_id:
                return None, "Object ID required for OBJECT_RESIZED."
            
            obj_stmt = select(BoardObject).where(
                BoardObject.id == target_obj_id,
                BoardObject.board_id == msg.board_id
            )
            res_obj = await db.execute(obj_stmt)
            obj = res_obj.scalars().first()
            if not obj or obj.is_deleted:
                return None, f"Object {target_obj_id} not found."

            if "width" in payload:
                obj.width = float(payload["width"])
            if "height" in payload:
                obj.height = float(payload["height"])
            if "x" in payload:
                obj.x = float(payload["x"])
            if "y" in payload:
                obj.y = float(payload["y"])
            obj.version += 1
            obj.last_modified_by = user_id
            await db.flush()
            out_payload = {
                "id": obj.id,
                "x": obj.x,
                "y": obj.y,
                "width": obj.width,
                "height": obj.height,
                "version": obj.version
            }

        elif msg.type == WSMessageType.OBJECT_UPDATED:
            if not target_obj_id:
                return None, "Object ID required for OBJECT_UPDATED."

            obj_stmt = select(BoardObject).where(
                BoardObject.id == target_obj_id,
                BoardObject.board_id == msg.board_id
            )
            res_obj = await db.execute(obj_stmt)
            obj = res_obj.scalars().first()
            if not obj or obj.is_deleted:
                return None, f"Object {target_obj_id} not found."

            updatable_fields = [
                "text", "color", "fill", "stroke", "stroke_width",
                "rotation", "z_index", "properties"
            ]
            for field in updatable_fields:
                if field in payload:
                    setattr(obj, field, payload[field])
            
            obj.version += 1
            obj.last_modified_by = user_id
            await db.flush()
            out_payload = obj.to_dict()

        elif msg.type == WSMessageType.OBJECT_DELETED:
            if not target_obj_id:
                return None, "Object ID required for OBJECT_DELETED."

            obj_stmt = select(BoardObject).where(
                BoardObject.id == target_obj_id,
                BoardObject.board_id == msg.board_id
            )
            res_obj = await db.execute(obj_stmt)
            obj = res_obj.scalars().first()
            if obj:
                obj.is_deleted = True
                obj.version += 1
                obj.last_modified_by = user_id
                await db.flush()
            out_payload = {"id": target_obj_id, "is_deleted": True}

        # 5. Persist operation audit entry
        audit = BoardOperation(
            board_id=msg.board_id,
            user_id=user_id,
            operation_id=msg.operation_id or f"op_{board.revision}",
            op_type=msg.type.value,
            payload=out_payload,
            revision=new_revision,
        )
        db.add(audit)
        await db.flush()

        # 6. Construct broadcast message
        broadcast_msg = WSMessage(
            type=msg.type,
            board_id=msg.board_id,
            operation_id=msg.operation_id,
            object_id=target_obj_id,
            payload=out_payload,
            client_revision=msg.client_revision,
            server_revision=new_revision,
            user_id=user_id,
            user_name=user_name,
        )
        return broadcast_msg, None


collaboration_engine = CollaborationEngine()
