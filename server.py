import asyncio
import json
import websockets

SERVER_IP = "0.0.0.0"
SERVER_PORT = 8000
clients = {}
offers = {}
answers = {}
pending_offers = {}
pending_answers = {}


async def websocket_handler(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)
            user_id = data.get("user_id")
            print(f"Received data: {data}")
            target_user_id = data.get("target_user_id")

            clients[user_id] = websocket

            if user_id in pending_offers:
                print(f"Sending pending offer to {user_id}")
                await websocket.send(json.dumps(pending_offers[user_id]))
                del pending_offers[user_id]

            if data['type'] == 'register':
                if target_user_id in clients:
                    await websocket.send(json.dumps({"type": "request_answer"}))
                    await clients[target_user_id].send(json.dumps({"type": "request_offer"}))
                else:
                    print(f"User {user_id} registered but {target_user_id} is not connected.")

            elif data["type"] == "offer":
                offers[user_id] = {"sdp": data["sdp"], "type": "offer", "user_id": user_id}
                print(f"Offer saved for {user_id}")

                if target_user_id in clients:
                    await clients[target_user_id].send(json.dumps(offers[user_id]))
                    print(f"Offer sent to {target_user_id}")
                else:
                    pending_offers[target_user_id] = offers[user_id]

            elif data["type"] == "answer":
                answers[user_id] = {"sdp": data["sdp"], "type": "answer", "user_id": user_id}
                print(f"Answer saved for {user_id}")

                if target_user_id in clients:
                    await clients[target_user_id].send(json.dumps(answers[user_id]))
                    print(f"Answer sent to {target_user_id}")
                else:
                    pending_answers[target_user_id] = answers[user_id]

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
        offers.pop(user_id, None)
        answers.pop(user_id, None)
        print(f"Cleaned up user: {user_id}")


async def main():
    async with websockets.serve(websocket_handler, SERVER_IP, SERVER_PORT):
        print(f"WebSocket server is running on ws://{SERVER_IP}:{SERVER_PORT}")
        await asyncio.Future()

asyncio.run(main())
