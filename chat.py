from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

app = FastAPI()

# 👇 Дозволяємо звернення з фронтенду
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Тестові юзери
registered_users = {"alice", "bob", "charlie", "admin"}

# Читання повідомлень із файлу
with open("messages.json", "r") as f:
    messages_db = json.load(f)

class ChatRequest(BaseModel):
    user_id: str
    target_user_id: str

class MessageRequest(BaseModel):
    user_id: str
    target_user_id: str
    text: str
    timestamp: str

@app.get("/users")
def get_users():
    return list(registered_users)

@app.get("/get_chats/{user_id}")
def get_chats(user_id: str):
    if user_id not in registered_users:
        raise HTTPException(status_code=404, detail="User not found")
    return list(registered_users - {user_id})

@app.get("/get_messages/{user_id}/{target_user_id}")
def get_messages(user_id: str, target_user_id: str):
    key1 = f"{user_id}__{target_user_id}"
    key2 = f"{target_user_id}__{user_id}"
    return messages_db.get(key1) or messages_db.get(key2) or []

@app.post("/add_chat")
def add_chat(data: ChatRequest):
    if data.target_user_id not in registered_users:
        raise HTTPException(status_code=404, detail="Target user does not exist")
    return {"status": "chat added"}

@app.post("/send_message")
def send_message(msg: MessageRequest):
    key = f"{msg.user_id}__{msg.target_user_id}"
    if key not in messages_db:
        key = f"{msg.target_user_id}__{msg.user_id}"
    if key not in messages_db:
        messages_db[key] = []

    messages_db[key].append({
        "sender": "me",  # у твоїй логіці це завжди "me"
        "text": msg.text,
        "timestamp": msg.timestamp
    })

    # 👇 зберігаємо у файл
    with open("messages.json", "w") as f:
        json.dump(messages_db, f, indent=2)

    return {"status": "sent"}
