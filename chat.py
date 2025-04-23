from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

app = FastAPI()

# Allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat history stored in a dictionary
chat_data = {
    "me": [],
    "them": []
}

# Message model
class Message(BaseModel):
    sender: Literal["me", "them"]
    text: str
    timestamp: datetime

@app.get("/messages")
def get_messages():
    return chat_data

@app.post("/messages")
def add_message(msg: Message):
    if msg.sender in chat_data:
        chat_data[msg.sender].append({
            "text": msg.text,
            "timestamp": msg.timestamp.isoformat()
        })
        return {"status": "Message stored in " + msg.sender}
    return {"error": "Invalid sender"}, 400