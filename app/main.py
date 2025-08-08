from fastapi.responses import JSONResponse


from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from typing import AsyncIterable
import asyncio
import base64
import json


from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from fastapi import File, UploadFile, Form
from app.imoye.tools.gcs_upload import upload_file_to_gcs, GCSUploadError

from app.imoye.agent import rag_voice_agent, root_agent
from app.imoye.tools import (
    create_corpus,
    delete_corpus,
    add_data,
    delete_document,
    get_corpus_info,
    list_corpora,
    check_corpus_exists,
    get_corpus_resource_name,
    set_current_corpus,
)
from google.adk.tools.tool_context import ToolContext
from fastapi import Body
from typing import List, Optional

# --- RAG API endpoints ---
from fastapi import APIRouter
# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "info").upper(),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fastapi_app")

app = FastAPI(
    title="FastAPI Production Backend",
    version="1.0.0",
    debug=os.getenv("ENVIRONMENT", "production") != "production"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_NAME = "Imoye Streaming AI"
session_service = InMemorySessionService()


def start_agent_session(session_id, is_audio=False):
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=session_id,
        session_id=session_id,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=rag_voice_agent,
        session_service=session_service,
    )

    modality = "AUDIO" if is_audio else "TEXT"

    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
        )
    )
    
    # Fix: Pass the enum itself, not the string value  "speech_config": speech_config
    config = {"response_modalities": [modality],}
    if is_audio:
        config["output_audio_transcription"] = {}

    run_config = RunConfig(**config)

    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue


async def agent_to_client_messaging(websocket: WebSocket, live_events: AsyncIterable[Event | None]):
    try:
        async for event in live_events:
            if event is None:
                continue

            if event.turn_complete or event.interrupted:
                message = {
                    "turn_complete": event.turn_complete,
                    "interrupted": event.interrupted,
                }
                await websocket.send_text(json.dumps(message))
                logger.info(f"[AGENT ➡️ CLIENT]: {message}")
                continue

            part = event.content and event.content.parts and event.content.parts[0]
            if not part or not isinstance(part, types.Part):
                continue

            if part.text and event.partial:
                message = {
                    "mime_type": "text/plain",
                    "data": part.text,
                    "role": "model",
                }
                await websocket.send_text(json.dumps(message))
                logger.info(f"[AGENT ➡️ CLIENT]: text/plain: {part.text}")

            if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
                audio_data = part.inline_data.data
                if audio_data:
                    message = {
                        "mime_type": "audio/pcm",
                        "data": base64.b64encode(audio_data).decode("ascii"),
                        "role": "model",
                    }
                    await websocket.send_text(json.dumps(message))
                    logger.info(f"[AGENT ➡️ CLIENT]: audio/pcm: {len(audio_data)} bytes")
    except Exception as e:
        logger.error(f"[agent_to_client_messaging] Error: {str(e)}")


async def client_to_agent_messaging(websocket: WebSocket, live_request_queue: LiveRequestQueue):
    try:
        while True:
            message_json = await websocket.receive_text()
            message = json.loads(message_json)

            mime_type = message["mime_type"]
            data = message["data"]
            role = message.get("role", "user")

            if mime_type == "text/plain":
                content = types.Content(role=role, parts=[types.Part.from_text(text=data)])
                live_request_queue.send_content(content=content)
                logger.info(f"[CLIENT ➡️ AGENT]: text/plain: {data}")
            elif mime_type == "audio/pcm":
                decoded_data = base64.b64decode(data)
                live_request_queue.send_realtime(
                    types.Blob(data=decoded_data, mime_type=mime_type)
                )
                logger.info(f"[CLIENT ➡️ AGENT]: audio/pcm: {len(decoded_data)} bytes")
            else:
                logger.warning(f"[CLIENT ➡️ AGENT]: Unsupported mime type: {mime_type}")
    except Exception as e:
        logger.error(f"[client_to_agent_messaging] Error: {str(e)}")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, is_audio: str = Query("false")):
    try:
        await websocket.accept()
        logger.info(f"WebSocket client #{session_id} connected (audio mode: {is_audio})")

        is_audio_enabled = is_audio.lower() == "true"
        live_events, live_request_queue = start_agent_session(session_id, is_audio_enabled)

        await asyncio.gather(
            agent_to_client_messaging(websocket, live_events),
            client_to_agent_messaging(websocket, live_request_queue),
        )

    except WebSocketDisconnect:
        logger.warning(f"WebSocket client #{session_id} disconnected unexpectedly.")
    except Exception as e:
        logger.error(f"WebSocket error (session: {session_id}): {str(e)}", exc_info=True)
    finally:
        logger.info(f"WebSocket session #{session_id} closed.")


@app.get("/")
async def welcome():
    return {
        "message": "Welcome to the FastAPI Production Backend!",
        "timestamp": datetime.now().isoformat(),
        "status": "healthy"
    }

@app.post("/chat/{session_id}")
async def chat_with_agent(session_id: str, payload: dict):
    try:
        message = payload.get("message")
        if not message:
            raise HTTPException(status_code=400, detail="Message field is required")

        # Create a session if not already created
       
        session = session_service.create_session(
                app_name=APP_NAME,
                user_id=session_id,
                session_id=session_id,
            )

        # Setup runner
        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,  # make sure this agent supports non-streaming
            session_service=session_service,
        )

        # Prepare content for the agent
        content = types.Content(role="user", parts=[types.Part.from_text(text=message)])

        # Run a single request (non-streaming)
        result =  runner.run_async(session_id=session_id, new_message=content, user_id=session_id)

        # Parse result
        responses = []
        turn_complete = False
        async for item in result:
            if hasattr(item, "content") and hasattr(item.content, "parts"):
                parts = item.content.parts
                responses.extend([part.text for part in parts if isinstance(part, types.Part) and part.text])
            if hasattr(item, "turn_complete"):
                turn_complete = item.turn_complete

        if not responses:
            logger.warning(f"No valid responses received for session {session_id}")
            return {"responses": [], "turn_complete": turn_complete}

        return {
            "responses": responses,
            "turn_complete": turn_complete,
        }

    except Exception as e:
        logger.error(f"[Non-streaming agent] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Agent error")



@app.exception_handler(Exception)
async def exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )




rag_router = APIRouter(prefix="/rag", tags=["RAG"])

@rag_router.post("/create_corpus")
def api_create_corpus(corpus_name: str = Body(..., embed=True)):
    
    return create_corpus(corpus_name)

@rag_router.delete("/delete_corpus")
def api_delete_corpus(corpus_name: str, confirm: bool = True):
    tool_context = ToolContext()
    return delete_corpus(corpus_name, confirm, tool_context)

@rag_router.post("/add_document")
def api_add_document(corpus_name: str = Body(...), paths: List[str] = Body(...)):
    
    return add_data(corpus_name, paths)

@rag_router.delete("/delete_document")
def api_delete_document(corpus_name: str, document_id: str):
   
    return delete_document(corpus_name, document_id)

@rag_router.get("/get_corpus_info")
def api_get_corpus_info(corpus_name: str = Query(..., description="The name of the corpus to retrieve info for")):
    return get_corpus_info(corpus_name=corpus_name)

@rag_router.get("/list_corpora")
def api_list_corpora():
    return list_corpora()

# --- Utils endpoints ---



@rag_router.post("/upload_document")
def api_upload_document(
    corpus_name: str = Form(..., description="Target corpus name"),
    file: UploadFile = File(..., description="PDF, TXT, or DOCX file ≤ 40MB")
):
    """
    Upload a document (PDF, TXT, DOCX ≤40MB) to GCS and add to a RAG corpus.
    - Uploads the file to the configured GCS bucket.
    - Calls add_data with the GCS URL for the uploaded file.
    Returns the file URL and add_data result.
    """
    try:
        public_url, blob_name = upload_file_to_gcs(file)
    except GCSUploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"GCS upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file to GCS.")

    # Call add_data with the GCS URL
    add_result = add_data(corpus_name, [public_url])
    return {
        "status": "success",
        "file_url": public_url,
        "blob_name": blob_name,
        "add_data_result": add_result
    }

@rag_router.get("/check_corpus_exists")
def api_check_corpus_exists(corpus_name: str):
    return {"exists": check_corpus_exists(corpus_name)}

@rag_router.get("/get_corpus_resource_name")
def api_get_corpus_resource_name(corpus_name: str):
    return {"resource_name": get_corpus_resource_name(corpus_name)}

    

# Register the router
app.include_router(rag_router)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    logger.info(f"Starting FastAPI server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)