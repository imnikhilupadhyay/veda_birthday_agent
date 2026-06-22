import os
import uuid
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from rag_agent.generator import generator_agent, generator_agent_stream
from rag_agent.generator import generator_agent_stream, extract_user_profile_from_query
from rag_agent.history_store import (
    init_db,
    get_history,
    save_message,
    get_user_profile,
    upsert_user_name,
)
from rag_agent.config import COOKIE_NAME, MAX_HISTORY_MESSAGES
from rag_agent.generator import generator_agent_stream, extract_user_profile_from_query

from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

app = FastAPI(title="Veda Birthday Agent")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    thread_id = request.cookies.get(COOKIE_NAME)

    greeting = "Hi! How can I help you? 🎂"

    if thread_id:
        profile = get_user_profile(thread_id)
        if profile.get("name"):
            greeting = f"Hi {profile['name']}, good to see you again! How can I help you today? 🎂"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"greeting": greeting}
    )

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "").strip()

    if not user_message:
        return JSONResponse({
            "response": "Please ask me something about Veda's birthday."
        })

    thread_id = request.cookies.get(COOKIE_NAME)

    if not thread_id:
        thread_id = str(uuid.uuid4())

    history = get_history(
        thread_id,
        limit=MAX_HISTORY_MESSAGES
    )

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
        key=COOKIE_NAME,
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
            iter([json.dumps({
                "type": "token",
                "content": "Please ask me something about Veda's birthday."
            }) + "\n"]),
            media_type="application/x-ndjson"
        )

    thread_id = request.cookies.get(COOKIE_NAME)

    if not thread_id:
        thread_id = str(uuid.uuid4())

    history = get_history(thread_id, limit=MAX_HISTORY_MESSAGES)

    profile = get_user_profile(thread_id)

    extracted_profile = extract_user_profile_from_query(user_message)

    print("USER MESSAGE:", user_message, flush=True)
    print("EXTRACTED PROFILE:", extracted_profile, flush=True)
    print("THREAD ID:", thread_id, flush=True)

    if extracted_profile.get("name"):
        upsert_user_name(thread_id, extracted_profile["name"])
        profile["name"] = extracted_profile["name"]

    def stream_response():
        full_response = ""

        for event in generator_agent_stream(
            question=user_message,
            history=history,
            user_profile=profile,
        ):
            if event["type"] == "token":
                full_response += event["content"]

            yield json.dumps(event) + "\n"

        save_message(thread_id, "user", user_message)
        save_message(thread_id, "assistant", full_response)

    response = StreamingResponse(
        stream_response(),
        media_type="application/x-ndjson"
    )

    response.set_cookie(
        key=COOKIE_NAME,
        value=thread_id,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax"
    )

    return response

@app.get("/clear-session")
def clear_session():
    response = RedirectResponse(url="/")
    response.delete_cookie(COOKIE_NAME)
    return response

# @app.get("/debug-cookie")
# def debug_cookie(request: Request):
#     return {
#         "cookie": request.cookies.get(COOKIE_NAME)
#     }

# @app.get("/debug-profile")
# def debug_profile(request: Request):
#     thread_id = request.cookies.get(COOKIE_NAME)

#     if not thread_id:
#         return {"error": "no cookie"}

#     return get_user_profile(thread_id)

# @app.get("/debug-extract-name")
# def debug_extract_name(message: str):
#     return extract_user_profile_from_query(message)

# @app.get("/debug-save-name")
# def debug_save_name(request: Request):
#     thread_id = request.cookies.get(COOKIE_NAME)

#     if not thread_id:
#         return {"error": "no cookie"}

#     upsert_user_name(thread_id, "Rahul")

#     return {
#         "thread_id": thread_id,
#         "profile": get_user_profile(thread_id)
#     }


@app.get("/health")
def health():
    return {"status": "ok"}