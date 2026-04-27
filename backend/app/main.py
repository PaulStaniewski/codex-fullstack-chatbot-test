from fastapi import FastAPI

from app.routes import (
    auth_routes,
    chat_routes,
    conversation_routes,
    lesson_routes,
    message_routes,
    progress_routes,
)


app = FastAPI(title="Fullstack Chatbot API")

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(conversation_routes.router)
app.include_router(lesson_routes.router)
app.include_router(message_routes.router)
app.include_router(progress_routes.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
