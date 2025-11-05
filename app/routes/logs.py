# app/routes/logs.py
from fastapi import APIRouter, WebSocket
import asyncio
from app.utils.log_capture import log_buffer  # import the shared buffer

router = APIRouter()

@router.websocket("/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    try:
        last_seen = 0
        while True:
            if len(log_buffer) > last_seen:
                # get new lines since last_seen
                new_logs = list(log_buffer)[last_seen:]
                last_seen = len(log_buffer)
                for line in new_logs:
                    await websocket.send_text(line)
            else:
                await asyncio.sleep(0.5)
    except Exception:
        pass
    finally:
        await websocket.close()
