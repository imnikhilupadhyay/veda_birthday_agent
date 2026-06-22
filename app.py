import os
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from rag_agent.generator import generator_agent, generator_agent_stream
from rag_agent.history_store import init_db, get_history, save_message

from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

app = FastAPI(title="Veda Birthday Agent")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "").strip()

    if not user_message:
        return JSONResponse({
            "response": "Please ask me something about Veda's birthday."
        })

    thread_id = request.cookies.get("thread_id")

    if not thread_id:
        thread_id = str(uuid.uuid4())

    history = get_history(thread_id, limit=4)

    assistant_response = generator_agent(
        question=user_message,
        history=history
    )

    save_message(thread_id, "user", user_message)
    save_message(thread_id, "assistant", assistant_response)

    response = JSONResponse({
        "response": assistant_response
    })

    response.set_cookie(
        key="thread_id",
        value=thread_id,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax"
    )

    return response

@app.post("/chat-stream")
async def chat_stream(request: Request):
    body = await request.json()
    user_message = body.get("message", "").strip()

    if not user_message:
        return StreamingResponse(
            iter(["Please ask me something about Veda's birthday."]),
            media_type="text/plain"
        )

    thread_id = request.cookies.get("thread_id")

    if not thread_id:
        thread_id = str(uuid.uuid4())

    history = get_history(thread_id, limit=4)

    def stream_response():
        full_response = ""

        for token in generator_agent_stream(
            question=user_message,
            history=history
        ):
            full_response += token
            yield token

        save_message(thread_id, "user", user_message)
        save_message(thread_id, "assistant", full_response)

    response = StreamingResponse(
        stream_response(),
        media_type="text/plain"
    )

    response.set_cookie(
        key="thread_id",
        value=thread_id,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax"
    )

    return response


@app.get("/health")
def health():
    return {"status": "ok"}