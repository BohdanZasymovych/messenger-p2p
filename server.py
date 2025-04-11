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


# async def connect_users(offerer_id, answerer_id):
#     print("Connecting users")
#     offerer_websocket = clients[offerer_id].websocket
#     answerer_websocket = clients[answerer_id].websocket

#     offer = await offerer_websocket.recv()
#     print(f"Get offer: {offer}\n")
#     await answerer_websocket.send(offer)

#     answer = await answerer_websocket.recv()
#     print(f"Get answer: {answer}\n")
#     await offerer_websocket.send(answer)


async def connect_offer(websocket, target_user_id):

    target_user_websocket = clients[target_user_id].websocket

    offer = await websocket.recv()
    print(f"Get offer: {offer}\n")
    await target_user_websocket.send(offer)

    # answer = await target_user_websocket.recv()
    # print(f"Get answer: {answer}\n")
    # websocket.send(answer)

    # pending_data["offer"][offer.content["target_user_id"]] = {
    #     "sdp": offer.content["sdp"],
    #     "type": "offer",
    #     "offerer_id": user_id}


async def connect_answer(websocket, target_user_id):

    target_user_websocket = clients[target_user_id].websocket

    answer = await websocket.recv()
    print(f"Get answer: {answer}\n")
    await target_user_websocket.send(answer)


async def websocket_handler(websocket):
    print("New client connected.")
    try:
        async for request in websocket:
            data = Request.from_string(request)
            print(f"Request: {data.json_string}\n")
            request_type = data.type
            user_id = data.content["user_id"]

            if request_type == "connect_to":
                target_user_id = data.content["target_user_id"]
                # connect_to_request = Request.from_string(connect_to_request)
                # print(f"Connect to request recieved: {connect_to_request}")
                role = data.content["role"]
                if role == "offer":
                    await connect_offer(websocket, target_user_id)
                elif role == "answer":
                    await connect_answer(websocket, target_user_id)

            elif request_type == "register_request":
                if user_id in clients:
                    clients[user_id].websocket = websocket
                else:
                    clients[user_id] = User(websocket)
                clients[user_id].is_online = True
                # clients.setdefault(user_id, User(websocket)).is_online = True

                # Here stored messages should be sent to the user as one request
                # Messages should be ordered in some way
                target_user_id = clients[user_id].pending_user_id
                if clients[user_id].is_pended:
                    connection_establishment_request = Request(
                        request_type="connection_request",
                        content={"user_id": clients[user_id].pending_user_id, "role": "answer"}
                    )
                    await websocket.send(connection_establishment_request.json_string)
                    print(f"Connection establishment request sent: {connection_establishment_request.json_string}")
                    clients[user_id].role = "answer"

                    connection_establishment_request = Request(
                        request_type="connection_request",
                        content={"user_id": user_id, "role": "offer"}
                    )
                    await clients[target_user_id].websocket.send(connection_establishment_request.json_string)
                    print(f"Connection establishment request sent: {connection_establishment_request.json_string}")
                    clients[target_user_id].role = "offer"

                    # await connect_users(offerer_id=user_id, answerer_id=target_user_id)
                    await connect_answer(websocket, target_user_id)
                else:
                    wait_request = Request(
                    request_type="wait_request",
                    content={"role": "offer"}
                    )
                    await websocket.send(wait_request.json_string)
                    print(f"Wait request sent: {wait_request.json_string}")
                    clients[user_id].role = "offer"

                    # connect_to_request = await websocket.recv()
                    # connect_to_request = Request.from_string(connect_to_request)
                    # print(f"Connect to request recieved: {connect_to_request}")
                    # role = connect_to_request.content["role"]
                    # if role == "offer":
                    #     connect_offer(websocket, target_user_id)
                    # elif role == "answer":
                    #     connect_answer(websocket, target_user_id)
                    # connection_establishment_request = await websocket.recv()
                    # await connect_offer(websocket, target_user_id)

            elif request_type == "connection_request":
                target_user_id = data.content["target_user_id"]

                if target_user_id not in clients:
                    error_request = Request(
                        request_type="client_not_registered_error",
                        content={}
                    )
                    await websocket.send(error_request.json_string)

                elif clients[target_user_id].is_online:
                    connection_establishment_request = Request(
                        request_type="connection_establishment_request",
                        content={"user_id": user_id, "role": "answer"}
                    )
                    await clients[target_user_id].websocket.send(connection_establishment_request.json_string)
                    print(f"Connection establishment request sent to answerer: {connection_establishment_request.json_string}")
                    clients[target_user_id].role = "answer"

                    connection_establishment_request = Request(
                        request_type="connection_establishment_request",
                        content={"role": "offer"}
                    )
                    await websocket.send(connection_establishment_request.json_string)
                    print(f"Connection establishment request sent to offerer: {connection_establishment_request.json_string}")
                    clients[target_user_id].role = "offer"

                    await connect_offer(websocket, target_user_id)
                    # await connect_users(offerer_id=user_id, answerer_id=target_user_id)

                else:
                    clients[target_user_id].is_pended = True
                    clients[target_user_id].pending_user_id = user_id
                    clients[user_id].pended_user_id = target_user_id

            elif request_type == "connect_to":
                role = request.content["role"]
                target_user_id = request.content["target_user_id"]
                match role:
                    case "offer":
                        await connect_offer(websocket, target_user_id)
                    case "answer":
                        await connect_answer(websocket, target_user_id)
                    case _:
                        raise ValueError("Incorrect role.")
            else:
                raise ValueError("Incorrect request type.")

    except json.JSONDecodeError:
        print("Error: Received invalid JSON")
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for user: {user_id}")
    finally:
        disconnect_user(user_id)
        await websocket.close()


def disconnect_user(user_id):
    if user_id:
        disconnected_user = clients[user_id]
        if disconnected_user.pended_user_id:
            clients[disconnected_user.pended_user_id].is_pended = False
            clients[disconnected_user.pended_user_id].pending_user_id = None
        clients[user_id].disconnect()
        print(f"Disconnected user: {user_id}")


async def main():
    async with websockets.serve(websocket_handler, SERVER_IP, SERVER_PORT):
        print(f"WebSocket server is running on ws://{SERVER_IP}:{SERVER_PORT}")
        await asyncio.Future()

asyncio.run(main())
