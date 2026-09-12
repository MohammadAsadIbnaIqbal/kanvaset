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
                logger.info("Ignoring duplicate operation %s and returning ACK", msg.operation_id)
                b_stmt = select(Board).where(Board.id == msg.board_id)
                b_res = await db.execute(b_stmt)
                b_obj = b_res.scalars().first()
                rev = b_obj.revision if b_obj else 0
                return WSMessage(
                    type=WSMessageType.ACK,
                    board_id=msg.board_id,
                    operation_id=msg.operation_id,
                    server_revision=rev,
                ), None

        # 3. Load Board and increment monotonic revision with pessimistic row lock
        board_stmt = select(Board).where(Board.id == msg.board_id).with_for_update()
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
            
            # Check if object exists globally
            global_stmt = select(BoardObject).where(BoardObject.id == target_obj_id)
            res_global = await db.execute(global_stmt)
            existing_global = res_global.scalars().first()
            if existing_global and existing_global.board_id != msg.board_id:
                return None, f"Object ID '{target_obj_id}' belongs to another board."

            obj = existing_global
            try:
                if obj:
                    # Revive or update if already present
                    obj.is_deleted = False
                    obj.type = str(payload.get("type", obj.type))
                    if "x" in payload:
                        obj.x = float(payload["x"])
                    if "y" in payload:
                        obj.y = float(payload["y"])
                    if "width" in payload:
                        obj.width = max(float(payload["width"]), 1.0)
                    if "height" in payload:
                        obj.height = max(float(payload["height"]), 1.0)
                    if "rotation" in payload:
                        obj.rotation = float(payload["rotation"])
                    if "z_index" in payload:
                        obj.z_index = int(payload["z_index"])
                    obj.color = payload.get("color", obj.color)
                    obj.fill = payload.get("fill", obj.fill)
                    obj.stroke = payload.get("stroke", obj.stroke)
                    if "stroke_width" in payload:
                        obj.stroke_width = max(float(payload["stroke_width"]), 0.0)
                    obj.text = str(payload.get("text", obj.text or ""))
                    if "properties" in payload and isinstance(payload["properties"], dict):
                        obj.properties = payload["properties"]
                    obj.version += 1
                    obj.last_modified_by = user_id
                else:
                    obj = BoardObject(
                        id=target_obj_id,
                        board_id=msg.board_id,
                        type=str(payload.get("type", "rectangle")),
                        x=float(payload.get("x", 0.0)),
                        y=float(payload.get("y", 0.0)),
                        width=max(float(payload.get("width", 120.0)), 1.0),
                        height=max(float(payload.get("height", 80.0)), 1.0),
                        rotation=float(payload.get("rotation", 0.0)),
                        z_index=int(payload.get("z_index", 0)),
                        color=payload.get("color", "#ffffff"),
                        fill=payload.get("fill", "#ffffff"),
                        stroke=payload.get("stroke", "#000000"),
                        stroke_width=max(float(payload.get("stroke_width", 1.5)), 0.0),
                        text=str(payload.get("text", "")),
                        properties=payload.get("properties", {}) if isinstance(payload.get("properties"), dict) else {},
                        version=1,
                        is_deleted=False,
                        created_by=user_id,
                        last_modified_by=user_id,
                    )
                    db.add(obj)
                
                await db.flush()
                await db.refresh(obj)
                out_payload = obj.to_dict()
            except (ValueError, TypeError) as e:
                return None, f"Invalid value in operation payload: {str(e)}"

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

            try:
                if "x" in payload:
                    obj.x = float(payload["x"])
                if "y" in payload:
                    obj.y = float(payload["y"])
            except (ValueError, TypeError) as e:
                return None, f"Invalid numeric value in payload: {str(e)}"

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

            try:
                if "width" in payload:
                    obj.width = max(float(payload["width"]), 1.0)
                if "height" in payload:
                    obj.height = max(float(payload["height"]), 1.0)
                if "x" in payload:
                    obj.x = float(payload["x"])
                if "y" in payload:
                    obj.y = float(payload["y"])
            except (ValueError, TypeError) as e:
                return None, f"Invalid numeric value in payload: {str(e)}"

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

            try:
                if "text" in payload:
                    obj.text = str(payload["text"])
                if "color" in payload:
                    obj.color = str(payload["color"])
                if "fill" in payload:
                    obj.fill = str(payload["fill"])
                if "stroke" in payload:
                    obj.stroke = str(payload["stroke"])
                if "stroke_width" in payload:
                    obj.stroke_width = max(float(payload["stroke_width"]), 0.0)
                if "rotation" in payload:
                    obj.rotation = float(payload["rotation"])
                if "z_index" in payload:
                    obj.z_index = int(payload["z_index"])
                if "properties" in payload and isinstance(payload["properties"], dict):
                    obj.properties = payload["properties"]
            except (ValueError, TypeError) as e:
                return None, f"Invalid value in payload: {str(e)}"

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
            if not obj or obj.is_deleted:
                return None, f"Object {target_obj_id} not found."

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
