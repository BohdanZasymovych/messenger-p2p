from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registered users — only these can be used to create chats
registered_users = {"admin", "testuser", "alice", "bob", "me"}

# Data storage: user_id -> target_user_id -> messages
chat_store: Dict[str, Dict[str, List[Dict]]] = {}

# Models
class ChatCreate(BaseModel):
    user_id: str
    target_user_id: str

class Message(BaseModel):
    user_id: str
    target_user_id: str
    text: str
    timestamp: datetime

# Add a chat between two users
@app.post("/add_chat")
def add_chat(data: ChatCreate):
    if data.target_user_id not in registered_users:
        raise HTTPException(status_code=404, detail="User does not exist")

    if data.user_id not in chat_store:
        chat_store[data.user_id] = {}
    if data.target_user_id not in chat_store[data.user_id]:
        chat_store[data.user_id][data.target_user_id] = []

    return {"target_user_id": data.target_user_id}

# Send a message
@app.post("/send_message")
def send_message(msg: Message):
    # Save for sender
    if msg.user_id not in chat_store:
        chat_store[msg.user_id] = {}
    if msg.target_user_id not in chat_store[msg.user_id]:
        chat_store[msg.user_id][msg.target_user_id] = []

    chat_store[msg.user_id][msg.target_user_id].append({
        "text": msg.text,
        "timestamp": msg.timestamp.isoformat(),
        "sender": "me"
    })

    # Save for receiver
    if msg.target_user_id not in chat_store:
        chat_store[msg.target_user_id] = {}
    if msg.user_id not in chat_store[msg.target_user_id]:
        chat_store[msg.target_user_id][msg.user_id] = []

    chat_store[msg.target_user_id][msg.user_id].append({
        "text": msg.text,
        "timestamp": msg.timestamp.isoformat(),
        "sender": "them"
    })

    return {"status": "Message sent"}

# Get messages for a specific chat
@app.get("/get_messages/{user_id}/{target_user_id}")
def get_messages(user_id: str, target_user_id: str):
    return chat_store.get(user_id, {}).get(target_user_id, [])

# Get list of user's chats
@app.get("/get_chats/{user_id}")
def get_chats(user_id: str):
    return list(chat_store.get(user_id, {}).keys())

# Get list of all available user IDs
@app.get("/users")
def get_users():
    return list(registered_users)
