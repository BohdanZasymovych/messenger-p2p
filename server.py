import asyncio
import json
import websockets

SERVER_IP = "0.0.0.0"
SERVER_PORT = 8000
clients = {}
pending_data = {
    "offer": {},
    "answer": {}
}


async def websocket_handler(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)
            user_id = data.get("user_id")
            print(f"Received data: {data}")
            target_user_id = data.get("target_user_id")
            msg_type = data.get("type")

            clients[user_id] = websocket

            if user_id in pending_data["offer"]:
                print(f"Sending pending offer to {user_id}")
                await websocket.send(json.dumps(pending_data['offer'].pop([user_id])))

            if data['type'] == 'register':
                if target_user_id in clients:
                    await websocket.send(json.dumps({"type": "request_answer"}))
                    await clients[target_user_id].send(json.dumps({"type": "request_offer"}))
                else:
                    print(f"User {user_id} registered but {target_user_id} is not connected.")

            elif msg_type in ("offer", "answer"):
                payload = {
                    "sdp": data["sdp"],
                    "type": msg_type,
                    "target_user_id": target_user_id,
                    "user_id": user_id
                }

                pending_data[msg_type][user_id] = payload

                if target_user_id in clients:
                    await clients[target_user_id].send(json.dumps(payload))
                    print(f"{msg_type.capitalize()} sent to {target_user_id}")
                else:
                    pending_data[msg_type][target_user_id] = payload
                    print(f"{msg_type.capitalize()} stored for {target_user_id}")

    except json.JSONDecodeError:
        print("Error: Received invalid JSON")
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for user: {user_id}")
    finally:
        clear_data(user_id)
        await websocket.wait_closed()

def clear_data(user_id):
    if user_id:
        clients.pop(user_id, None)
        for store in pending_data.values():
            store.pop(user_id, None)
        print(f"Cleaned up user: {user_id}")



async def main():
    async with websockets.serve(websocket_handler, SERVER_IP, SERVER_PORT):
        print(f"WebSocket server is running on ws://{SERVER_IP}:{SERVER_PORT}")
        await asyncio.Future()

asyncio.run(main())
