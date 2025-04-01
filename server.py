import asyncio
import json
import websockets

clients = {}
offers = {}

async def websocket_handler(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)

            print(f"Received data: {data}")

            user_id = data.get("user_id")
            if user_id:
                clients[user_id] = websocket

            if data["type"] == "offer":
                offers[user_id] = {'sdp': data['sdp'], 'type': data['type']}
                print(f"Offer saved for user {user_id}: {offers[user_id]}")
                if "answerer" in clients:
                    await clients["answerer"].send(json.dumps(offers[user_id]))

            elif data["type"] == "answer" and "offerer" in clients:
                await clients["offerer"].send(json.dumps(data))

            elif data["type"] == "register" and user_id == "answerer":
                if offers:
                    for _, offer_data in offers.items():
                        await websocket.send(json.dumps(offer_data))

    except json.JSONDecodeError:
        print("Error: Received invalid JSON")
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for user: {user_id}")
        if user_id in clients:
            del clients[user_id]

async def main():
    async with websockets.serve(websocket_handler, "localhost", 8000):
        print("WebSocket сервер запущено на ws://localhost:8000/")
        await asyncio.Future()

asyncio.run(main())
