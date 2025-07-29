from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Dict
import json
import os
import logging
import uuid
from starlette.websockets import WebSocketState

from langchain_core.messages import AIMessage

from agents.coach_agent import InterviewCoachAgent
from models.interview_state import InterviewState, InterviewMetrics
from models.user_profile import UserProfile
from utils.storage import InterviewStorage

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

active_connections: Dict[str, WebSocket] = {}

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open(os.path.join("static", "index.html")) as f:
        return HTMLResponse(content=f.read())


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    coach = InterviewCoachAgent()
    storage = InterviewStorage()

    user_profile = storage.get_user_profile(client_id)
    if not user_profile:
        user_profile = UserProfile(
            user_id=client_id,
            name="Anonymous",
            email="anonymous@example.com",
            target_roles=[],
            current_level="mid",
            skills=[]
        )
        storage.save_user_profile(user_profile)

    async def send_message(type, data):
        try:
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps({"type": type, **data}))
        except Exception as e:
            logging.error(f"WebSocket send error: {e}")

    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message["type"] == "start_interview":
                    initial_state = InterviewState(
                        interview_id=f"mock_{uuid.uuid4().hex[:8]}",
                        user_id=client_id,
                        interview_type=message.get("interview_type", "software_engineer"),
                        level=message.get("level", "mid"),
                        current_phase="intro",
                        current_question="",
                        question_history=[],
                        user_responses=[],
                        feedback=[],
                        metrics=InterviewMetrics(),
                        conversation_context="",
                        start_time=None,
                        end_time=None,
                        resume_text=message.get("resume_text", ""),
                        use_voice=False  # Disable voice recognition
                    )

                    async for step in coach.run_interview(initial_state):
                        if websocket.application_state != WebSocketState.CONNECTED:
                            break

                        for msg in step.get("messages", []):
                            if isinstance(msg, AIMessage) and not msg.content.startswith("Feedback:"):
                                await send_message("question", {"question": msg.content})
                            elif isinstance(msg, AIMessage) and msg.content.startswith("Feedback:"):
                                await send_message("feedback", {"feedback": step.get("feedback", {})})

                        if step.get("summary"):
                            await send_message("summary", {"summary": step["summary"]})
                            # Close connection with normal closure code
                            if websocket.application_state == WebSocketState.CONNECTED:
                                await websocket.close(code=1000)
                            break  # Exit the interview loop

                elif message["type"] == "response":
                    # Directly process text responses without voice fallback
                    if hasattr(coach, 'voice'):
                        coach.voice._last_response = message["response"]
                    await send_message("ack", {"message": "Response received"})

                    # Force process the response immediately
                    if hasattr(coach, 'process_text_response'):
                        await coach.process_text_response(message["response"])

            except WebSocketDisconnect:
                logging.info(f"WebSocket disconnected for client {client_id}")
                break
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
                await send_message("error", {"message": str(e)})
                break

    finally:
        if client_id in active_connections:
            del active_connections[client_id]
        if websocket.application_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close()
            except Exception as e:
                logging.error(f"Error closing WebSocket: {e}")