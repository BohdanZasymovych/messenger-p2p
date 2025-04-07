import asyncio
import json
import websockets
from objects import User, Request


SERVER_IP = "0.0.0.0"
SERVER_PORT = 8000
clients = {} # client_id: User
pending_data = {
    "offer": {}, # target_user_id: offer_dict
    "answer": {}
}


async def connect_offer(websocket, user_id):
    role = Request(
            request_type="assign_role",
            content={"role": "offer"}
        )
    await websocket.send(role.json_string)
    print(f"Assign role: {role.json_string}\n")
    clients[user_id].role = "offer"

    offer = await websocket.recv()
    offer = Request.from_string(offer)
    print(f"Get offer: {offer.json_string}\n")
    pending_data["offer"][offer.content["target_user_id"]] = {
        "sdp": offer.content["sdp"],
        "type": "offer",
        "offerer_id": user_id}


async def connect_answer(websocket, user_id):
    role = Request(
            request_type="assign_role",
            content={"role": "answer"}
        )
    await websocket.send(role.json_string)
    print(f"Assign role: {role.json_string}\n")
    clients[user_id].role = "answer"

    offer = pending_data["offer"][user_id]
    target_user_id = offer["offerer_id"]
    del pending_data["offer"][user_id]

    offer = Request(
        request_type="offer",
        content=offer
    )
    await websocket.send(offer.json_string)
    print(f"Send offer: {offer.json_string}\n")

    answer = await websocket.recv()
    answer = Request.from_string(answer)
    print(f"Get answer: {answer.json_string}\n")

    answer = Request(
        request_type="answer",
        content=answer.content
    )
    await clients[target_user_id].websocket.send(answer.json_string)
    print(f"Send answer: {answer.json_string}\n")


async def websocket_handler(websocket):
    print("New client connected.")
    try:
        async for request in websocket:
            data = Request.from_string(request)
            print(f"Request: {data.json_string}\n")
            request_type = data.type
            user_id = data.content["user_id"]

            if request_type == "register":
                clients[user_id] = User(None, None, websocket)

                if user_id in pending_data["offer"]:
                    connection_request = Request(
                        request_type="connection_request",
                        content={}
                    )
                    await websocket.send(connection_request.json_string)

                    clients[user_id].role = "answer"
                    await connect_answer(websocket, user_id)
                else:
                    wait_request = Request(
                    request_type="wait_request",
                    content={}
                    )
                    await websocket.send(wait_request.json_string)

                    # role = Request(
                    #         request_type="assign_role",
                    #         content={"role": "answer"}
                    #     )
                    # await websocket.send(role.json_string)
                    # print(f"Assign role: {role.json_string}\n")

                #     offer = pending_data["offer"][user_id]
                #     target_user_id = pending_data["offer"][user_id]["offerer_id"]
                #     del pending_data["offer"][user_id]
                #     offer = Request(
                #         request_type="offer",
                #         content=offer
                #     )
                #     await websocket.send(offer.json_string)
                #     print(f"Send offer: {offer.json_string}\n")

                #     answer = await websocket.recv()
                #     answer = Request.from_string(answer)
                #     print(f"Get answer: {answer.json_string}\n")

                #     answer = answer.content
                #     answer = Request(
                #         request_type="answer",
                #         content=answer
                #     )
                #     await clients[target_user_id].websocket.send(answer.json_string)
                #     print(f"Send answer: {answer.json_string}\n")

###########################
            elif request_type == "connection":
                print(f"\nPending data: {pending_data}\n")

                if user_id in pending_data["offer"]:
                    await connect_answer(websocket, user_id)
                    # print(user_id in pending_data["offer"])
                    # role = Request(
                    #         request_type="assign_role",
                    #         content={"role": "answer"}
                    #     )
                    # await websocket.send(role.json_string)
                    # print(f"Assign role: {role.json_string}\n")
                    # clients[user_id].role = "answer"

                    # offer = pending_data["offer"][user_id]
                    # target_user_id = offer["offerer_id"]
                    # del pending_data["offer"][user_id]

                    # offer = Request(
                    #     request_type="offer",
                    #     content=offer
                    # )
                    # await websocket.send(offer.json_string)
                    # print(f"Send offer: {offer.json_string}\n")

                    # answer = await websocket.recv()
                    # answer = Request.from_string(answer)
                    # print(f"Get answer: {answer.json_string}\n")

                    # answer = Request(
                    #     request_type="answer",
                    #     content=answer.content
                    # )
                    # await clients[target_user_id].websocket.send(answer.json_string)
                    # print(f"Send answer: {answer.json_string}\n")


                else:
                    await connect_offer(websocket, user_id)
                    # role = Request(
                    #         request_type="assign_role",
                    #         content={"role": "offer"}
                    #     )
                    # await websocket.send(role.json_string)
                    # print(f"Assign role: {role.json_string}\n")
                    # clients[user_id].role = "offer"

                    # offer = await websocket.recv()
                    # offer = Request.from_string(offer)
                    # print(f"Get offer: {offer.json_string}\n")
                    # pending_data["offer"][offer.content["target_user_id"]] = {
                    #     "sdp": offer.content["sdp"],
                    #     "type": "offer",
                    #     "offerer_id": user_id}

            else:
                raise ValueError("Incorrect request type")

    except json.JSONDecodeError:
        print("Error: Received invalid JSON")
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for user: {user_id}")
    finally:
        disconnect_user(user_id)
        await websocket.wait_closed()


def disconnect_user(user_id):
    if user_id:
        clients[user_id].disconnect()
        for store in pending_data.values():
            store.pop(user_id, None)
        print(f"Disconnected user: {user_id}")


async def main():
    async with websockets.serve(websocket_handler, SERVER_IP, SERVER_PORT):
        print(f"WebSocket server is running on ws://{SERVER_IP}:{SERVER_PORT}")
        await asyncio.Future()

asyncio.run(main())
