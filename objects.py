import json
import asyncio
from aiortc import (RTCPeerConnection,
                    RTCSessionDescription,
                    RTCDataChannel,
                    RTCConfiguration,
                    RTCIceServer)
import websockets


ICE_CONFIG = RTCConfiguration(
    iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
)

SERVER_URL = "ws://0.0.0.0:8000"


class User:
    def __init__(self, websocket):
        self.is_online = True
        self.role = None
        self.is_pended = False
        self.pending_user_id = None
        self.pended_user_id = None
        self.connection_type = None
        self.websocket = websocket
        self.message_queue = asyncio.Queue()

    def add_message(self, message: 'Message'):
        self.message_queue.put_nowait(message.json_string)

    def disconnect(self):
        self.is_online = False
        self.role = None
        self.is_pended = False
        self.pending_user_id = None
        self.pended_user_id = None
        self.connection_type = None
        self.websocket = None


class Message:
    """Class to represent message exchanged between users"""
    def __init__(self, message_type: str, content: str, sending_time: str):
        self.type = message_type
        self.content = content
        self.sending_time = sending_time
        # self.user_id = user_id
        # self.target_user_id = target_user_id

    @property
    def json_string(self):
        """Converts message object to json string"""
        return json.dumps(
            {"type": self.type,
            "content": self.content,
            "sending_time": self.sending_time
            # "user_id": self.user_id,
            # "target_user_id": self.target_user_id
            })

    @classmethod
    def from_string(cls, json_string: str) -> 'Message':
        data = json.loads(json_string)
        return Message(
            message_type=data['type'],
            content=data['content'],
            sending_time=data['sending_time']
            # user_id=data['user_id'],
            # target_user_id=data['target_user_id']
        )


class Request:
    """Class to represent request to or from server"""
    def __init__(self, request_type: str, content: str, user_id: str=None):
        self.type = request_type
        self.user_id = user_id
        self.content = content

    @property
    def json_string(self):
        """Converts request object to json string"""
        return json.dumps(
            {"type": self.type, "user_id": self.user_id, "content": self.content}
            )

    @classmethod
    def from_string(cls, json_string: str) -> 'Request':
        data = json.loads(json_string)
        return Request(
            request_type=data["type"],
            user_id=data["user_id"],
            content=data["content"]
        )


class Connection:
    """Class to represent connection between to users"""
    def __init__(self, user_id: str, target_user_id: str):
        self.user_id = user_id
        self.target_user_id = target_user_id
        self.peer_connection: RTCPeerConnection | None = None
        self.data_channel: RTCDataChannel | None = None
        self.websocket = None

        self.connection_type = None
        self.is_connected_websocket = False
        self.is_p2p_connected = asyncio.Event()
        self.p2p_connection_state = "disconnected"

        self.local_connection_initiated = asyncio.Event()
        self.data_channel_opening_event = asyncio.Event()
        self.data_channel_closing_event = asyncio.Event()

        self.role = None

    async def p2p_disconnect(self):
        if self.peer_connection:
            await self.peer_connection.close()

        if self.data_channel and self.data_channel.readyState == "open":
            await self.data_channel.close()

        self.peer_connection = None
        self.data_channel = None
        self.p2p_connection_state = "disconnected"
        self.is_p2p_connected.clear()
        self.local_connection_initiated.clear()
        self.data_channel_opening_event.clear()
        self.data_channel_closing_event.clear()
        self.connection_type = None
        self.role = None

    async def server_disconect(self):
        if self.websocket:
            await self.websocket.close()

        self.is_connected_websocket = False
        self.websocket = None

    @staticmethod
    def __set_peer_connection_events(peer_connection: RTCPeerConnection) -> None:
        """Set events behavior for data channel"""
        @peer_connection.on("connectionstatechange")
        def on_connection_state_change():
            # logging.info("Connection state changed: %s", peer_connection.connectionState)
            print("Connection state changed: %s", peer_connection.connectionState)

        @peer_connection.on("iceconnectionstatechange")
        def on_ice_state_change():
            # logging.info("Ice connection state changed: %s", peer_connection.iceConnectionState)
            print("Ice connection state changed: %s", peer_connection.iceConnectionState)

        @peer_connection.on("icegatheringstatechange")
        def on_ice_gathering_change():
            # logging.info("Ice gathering state changed: %s", peer_connection.iceGatheringState)
            print("Ice gathering state changed: %s", peer_connection.iceGatheringState)

        @peer_connection.on("signalingstatechange")
        def on_signaling_state_change():
            # logging.info("Signaling state changed: %s", peer_connection.signalingState)
            print("Signaling state changed: %s", peer_connection.signalingState)

    def __set_data_channel_events(self, data_channel: RTCDataChannel) -> None:
        """Set events behavior for data channel"""
        @data_channel.on("error")
        def on_error(error):
            print("Data channel error:", error)
            # logging.error("Data channel error: %s", error)

        @data_channel.on('message')
        def on_message(message):
            message = Message.from_string(message)
            if message.type != "message":
                raise ValueError("Incorrect message type")
            print(f"Peer ({message.sending_time}): {message.content}")
            # logging.debug("Message received: %s", message)

        @data_channel.on('close')
        def on_close():
            print('\nData channel was closed')
            self.is_p2p_connected.clear()
            self.local_connection_initiated.clear()
            self.p2p_connection_state = "disconnected"

    async def __connect_offer(self) -> bool:
        """Function to connect as offerer"""

        # Create peer connection
        pc = RTCPeerConnection(configuration=ICE_CONFIG)
        self.peer_connection = pc

        # Set behavior for connection state change
        self.__set_peer_connection_events(pc)

        # Create data channel and set its behavior on events
        dc = pc.createDataChannel('channel')
        self.__set_data_channel_events(dc)

        @dc.on('open')
        def on_open():
            print('Data channel is open')
            self.is_p2p_connected.set()

        # Create and set offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        offer_request = Request(
            request_type="share_offer",
            content={"type": pc.localDescription.type,
                    "sdp": pc.localDescription.sdp}
        )

        await self.websocket.send(offer_request.json_string)
        print(f"Offer sent: {offer_request.json_string}")

        response = await self.websocket.recv()
        data = Request.from_string(response)
        print(f"Received answer: {data.json_string}")

        if data.type != "share_answer":
            raise ValueError("Incorrect response")

        answer = data.content

        if answer["type"] == "answer":
            answer = RTCSessionDescription(sdp=answer["sdp"], type="answer")
            await pc.setRemoteDescription(answer)
            print("Remote description was set")
        else:
            raise ValueError("Incorrect response")

        try:
            await asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            self.data_channel = dc
            self.p2p_connection_state = "connected"
        except asyncio.TimeoutError:
            return False

        return True

    async def __connect_answer(self) -> bool:
        """Function to connect as answer"""

        pc = RTCPeerConnection(configuration=ICE_CONFIG)
        self.peer_connection = pc

        self.__set_peer_connection_events(pc)

        dc = None

        @pc.on('datachannel')
        async def on_datachannel(data_channel):
            print("Data channel received")
            self.__set_data_channel_events(data_channel)

            @data_channel.on('open')
            def on_open():
                print('Data channel is open')
                self.is_p2p_connected.set()

            if data_channel.readyState == "open":
                self.is_p2p_connected.set()

            nonlocal dc
            dc = data_channel

        response = await self.websocket.recv()
        data = Request.from_string(response)
        print(f"Received offer: {data.json_string}")

        if data.type != "share_offer":
            raise ValueError("Incorrect response")

        offer = data.content

        if offer["type"] == "offer":
            offer = RTCSessionDescription(sdp=offer["sdp"], type="offer")
            await pc.setRemoteDescription(offer)

            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            answer = Request(
                request_type="share_answer",
                content={"sdp": pc.localDescription.sdp,
                        "type": pc.localDescription.type}
            )

            await self.websocket.send(answer.json_string)
            print(f"Answer sent: {answer.json_string}")
        else:
            raise ValueError("Incorrect response type.")

        try:
            await asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            self.data_channel = dc
            self.p2p_connection_state = "connected"
        except asyncio.TimeoutError:
            return False

        return True

    # async def __parse_role(self, target_user_id: str):
    #     connection_request = Request(
    #             request_type="connection",
    #             user_id=self.user_id,
    #             content={"user_id": self.user_id, "target_user_id": target_user_id})

    #     await self.websocket.send(connection_request.json_string)
    #     print(f"Connection request sended: {connection_request.json_string}")

    #     response = await self.websocket.recv()
    #     role = Request.from_string(response)
    #     print(f"Role received: {role.json_string}")
    #     return role.content["role"]

    async def __establish_p2p_connection(self, role: str) -> RTCDataChannel | None:
        print("Establish p2p connection")
        match role:
            case "offer":
                is_p2p_connected = await self.__connect_offer()
            case "answer":
                is_p2p_connected = await self.__connect_answer()
            case _:
                raise ValueError("Incorrect role")

        return is_p2p_connected

    async def connect_to_server(self):

        websocket = await websockets.connect(SERVER_URL)
        self.websocket = websocket

        register_request = Request(
            request_type="register_request",
            content={"user_id": self.user_id}
        )

        await websocket.send(register_request.json_string)
        print(f"Register request sended: {register_request.json_string}")
        self.is_connected_websocket = True

        register_response = await websocket.recv()
        register_response = Request.from_string(register_response)
        print(f"Register response received: {register_response.json_string}")

        match register_response.type:
            case "connection_request":
                self.role = register_response.content["role"]
                await self.__establish_p2p_connection(self.role)

            case "wait_request":
                # connection_init_task = asyncio.create_task(wait_for_connection_init())
                
                receive_request_task = asyncio.create_task(self.websocket.recv())
                local_connection_task = asyncio.create_task(self.local_connection_initiated.wait())
                await asyncio.wait(
                    [
                        receive_request_task,
                        local_connection_task
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                )

                if not receive_request_task.done():
                    receive_request_task.cancel()

                try:
                    connection_request = await receive_request_task
                except asyncio.CancelledError:
                    return

                # if connection_request.type == "client_not_registered_error":
                #     raise ValueError("Target user is not registered")

                connection_request = Request.from_string(connection_request)
                self.role = connection_request.content["role"]
                answer_connection_request = Request(
                    request_type="connect_to",
                    content={"role": "answer", "user_id": self.user_id, "target_user_id": self.target_user_id}
                )
                await self.websocket.send(answer_connection_request.json_string)
                print(f"Connect to request sent: {answer_connection_request.json_string}")
                await self.__establish_p2p_connection(self.role)

            case _:
                raise ValueError("Incorrect register response")

    async def connect_to_peer(self) -> bool:
        self.p2p_connection_state = "connecting"

        connection_request = Request(
            request_type="connection_request",
            content={"user_id": self.user_id, "target_user_id": self.target_user_id}
        )
        await self.websocket.send(connection_request.json_string)
        print(f"Connection request sent: {connection_request.json_string}")

        connection_response = await self.websocket.recv()
        connection_response = Request.from_string(connection_response)
        print(f"Connection response sent: {connection_response.json_string}")


        if connection_response.type == "client_not_registered_error":
            raise ValueError("Target user is not registered")

        self.role = connection_response.content["role"]

        is_p2p_connected = await self.__establish_p2p_connection(self.role)

        if is_p2p_connected:
            self.connection_type = "p2p_connection"
            self.p2p_connection_state = "connected"
            return True
        return False


    async def connect(self) -> bool:
        self.local_connection_initiated.set()


        if self.is_p2p_connected.is_set():
            return

        if not self.is_connected_websocket:
            await self.connect_to_server()

        await asyncio.sleep(0.1)

        if self.p2p_connection_state == "connecting":
            try:
                asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            except asyncio.TimeoutError:
                raise Exception("Connection failed.")

        if self.p2p_connection_state == "disconnected":
            connection_result = await self.connect_to_peer()
            print(connection_result)
            return

        raise ValueError("Invalid p2p connection state")


        # self.role = await self.__parse_role(self.target_user_id)

        # is_p2p_connected = await self.__establish_p2p_connection(self.role)

        # if is_p2p_connected:
        #     self.connection_type = "p2p_connection"
        #     self.p2p_connection_state = "connected"
        #     return True
        # self.p2p_connection_state = "disconnected"
        # return False





# class Chat:
#     """Class to represent chat between two users"""
#     def __init__(self, user_id: str, target_user_id: str):
#         self.user_id = user_id
#         self.target_user_id = target_user_id
#         self.__message_queue = asyncio.Queue()
#         self.__connection = Connection(self.user_id, self.target_user_id)

#     async def message_loop(self):
#         """Asynchronous function which handles receiving messages"""
#         print()
#         while True:
#             message = await ainput('You: ')
#             if message:
#                 self.__message_queue.put_nowait(Message(message_type="message",
#                                                         content=message,
#                                                         sending_time=datetime.now().strftime('%H:%M:%S')))

#     async def send_message(self, message: Message):
#         connection = self.__connection
#         if connection.connection_state == "connected":
#             print('already connected')
#             connection.data_channel.send(message.json_string)
#         else:
#             print('need to connect connected')
#             is_connected = await connection.connect()
#             if is_connected:
#                 connection.data_channel.send(message.json_string)
#             else:
#                 raise Exception("Connection failed")

#     async def send_message_loop(self):
#         while True:
#             message = await self.__message_queue.get()
#             await self.send_message(message)
