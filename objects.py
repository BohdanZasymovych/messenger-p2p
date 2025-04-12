import json
import asyncio
from datetime import datetime
from aioconsole import ainput

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


class IncorrectRequestTypeError(Exception):
    """Exception which is raised when request with incorrect type is received"""


class ConnectionTimeoutError(Exception):
    """Exception which is raised when connection is not established within certain amount of time"""


class UserNotRegisteredError(Exception):
    """Exception which is raised when target user is not registered on server"""


class User:
    """Class that represents user on the server side"""
    def __init__(self, websocket=None):
        self.is_online = True # Indicates if user is connected to the server
        self.role = None 
        self.is_pended = False # Indicates if someone is waiting for user
        self.pending_user_id = None # User waiting for you
        self.pended_user_id = None # User you are waiting
        self.connection_type = None
        self.websocket = websocket
        self.message_queue = asyncio.Queue()

    def add_message(self, message: 'Message'):
        """Adds message to the queue"""
        self.message_queue.put_nowait(message.json_string)

    def disconnect(self):
        """Sets user to default disconnected state"""
        self.is_online = False
        self.role = None
        self.is_pended = False
        self.pending_user_id = None
        self.pended_user_id = None
        self.connection_type = None
        self.websocket = None


class Time:
    """Class to represent time"""
    def __init__(self, empty: bool=False):
        """
        Initializes time object with current time if empty parameter is False,
        or empty time object otherwise
        """
        if empty:
            self.date = None
            self.time = None
        else:
            cur_time =  datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            self.date = cur_time.split()[0]
            self.time = cur_time.split()[1]

    def __str__(self):
        """Returns string representation of time to seconds"""
        return self.time[:8]

    @property
    def json_string(self):
        """Returns json string representing time object"""
        return json.dumps(
            {"date": self.date, "time": self.time}
        )

    @classmethod
    def from_string(cls, json_string: str) -> 'Time':
        """Creates time object from json string"""
        time_obj = Time(empty=True)
        time_dict = json.loads(json_string)
        time_obj.date = time_dict["date"]
        time_obj.time = time_dict["time"]
        return time_obj


class Message:
    """Class to represent message exchanged between users"""
    def __init__(self, message_type: str, content: str, sending_time: Time,
                 user_id: str, target_user_id: str):

        self.type = message_type
        self.content = content
        self.sending_time = sending_time
        self.user_id = user_id
        self.target_user_id = target_user_id

    @property
    def json_string(self):
        """Converts message object to json string"""
        return json.dumps(
            {"type": self.type,
            "content": self.content,
            "sending_time": self.sending_time.json_string,
            "user_id": self.user_id,
            "target_user_id": self.target_user_id
            })

    @classmethod
    def from_string(cls, json_string: str) -> 'Message':
        """Creates message object from json string"""
        data = json.loads(json_string)
        return Message(
            message_type=data['type'],
            content=data['content'],
            sending_time=Time.from_string(data['sending_time']),
            user_id=data['user_id'],
            target_user_id=data['target_user_id']
        )

    def __str__(self):
        return f"User {self.user_id} ({self.sending_time}): {self.content}"


class Request:
    """Class to represent request to the server or from it"""
    def __init__(self, request_type: str, user_id: str=None, content: str=None):
        self.type = request_type
        self.user_id = user_id # id of user who sended request if server sended should be None 
        self.content = content if content is not None else {}

    @property
    def json_string(self):
        """Converts request object to json string"""
        return json.dumps(
            {"type": self.type, "user_id": self.user_id, "content": self.content}
            )

    @classmethod
    def from_string(cls, json_string: str) -> 'Request':
        """Creates request object from json string"""
        data = json.loads(json_string)
        return Request(
            request_type=data["type"],
            user_id=data["user_id"],
            content=data["content"]
        )

    def __str__(self):
        return self.json_string


class Connection:
    """Class to represent connection between to users"""
    def __init__(self, user_id: str, target_user_id: str):
        self.user_id = user_id
        self.target_user_id = target_user_id

        self.peer_connection: RTCPeerConnection | None = None
        self.data_channel: RTCDataChannel | None = None
        self.websocket = None

        # self.connection_type = None
        self.is_connected_websocket = False
        self.is_p2p_connected = asyncio.Event()
        self.p2p_connection_state = "disconnected"

        self.local_connection_initiated = asyncio.Event()
        self.local_disconnect_initialized = False
        self.data_channel_opening_event = asyncio.Event()
        self.data_channel_closing_event = asyncio.Event()

        self.role = None

        # Adds disconnect handler task to the event loop
        # __on_disconnect function will be ran each time data_channel_closing_event is being set
        asyncio.create_task(self.__on_disconnect())


    async def p2p_disconnect(self):
        """
        Disconnects user from server and
        runs function waiting for connection request if data channel was closed by another peer
        """
        print("p2p disconnect triggred")
        if self.data_channel is not None and self.data_channel.readyState == "open":
            self.data_channel.close()

        if self.peer_connection is not None:
            await self.peer_connection.close()

        self.is_p2p_connected.clear()
        self.local_connection_initiated.clear()
        self.p2p_connection_state = "disconnected"
        self.peer_connection = None
        self.data_channel = None
        self.is_p2p_connected.clear()
        # self.connection_type = None
        self.role = None

    async def server_disconect(self):
        """Disconnects user from the server"""
        if self.websocket:
            await self.websocket.close()

        self.is_connected_websocket = False
        self.websocket = None

    async def __on_disconnect(self) -> None:
        """
        Waits till data channel was closed, clears user
        and if disconnect was initialized by another peer
        launches function waiting for connection request
        """
        while True:
            await self.data_channel_closing_event.wait()
            self.data_channel_closing_event.clear()
            await self.p2p_disconnect()

            if self.local_disconnect_initialized:
                continue

            self.local_disconnect_initialized = False
            await self.__wait_for_connection_request()
            print("Websocket was closed")

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
                raise ValueError("Incorrect message type.")
            print(message)
            # logging.debug("Message received: %s", message)

        @data_channel.on('close')
        def on_close():
            print('\nData channel was closed')
            self.data_channel_closing_event.set()

    async def __connect_offer(self) -> bool:
        """Function to connect as offerer"""
        pc = RTCPeerConnection(configuration=ICE_CONFIG)
        self.peer_connection = pc
        self.__set_peer_connection_events(pc)

        dc = pc.createDataChannel('channel')
        self.__set_data_channel_events(dc)

        @dc.on('open')
        def on_open():
            print('Data channel is open')
            self.is_p2p_connected.set()

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        offer_request = Request(
            request_type="share_offer_request",
            user_id=self.user_id,
            content={"type": pc.localDescription.type,
                    "sdp": pc.localDescription.sdp}
        )
        await self.websocket.send(offer_request.json_string)
        print(f"Offer sent: {offer_request}")

        response = await self.websocket.recv()
        data = Request.from_string(response)
        print(f"Received answer: {data}")

        if data.type != "share_answer_request":
            raise IncorrectRequestTypeError("Incorrect response to offer")

        answer = data.content
        answer = RTCSessionDescription(sdp=answer["sdp"], type="answer")
        await pc.setRemoteDescription(answer)
        print("Remote description was set")

        try:
            await asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            self.data_channel = dc
            # self.p2p_connection_state = "connected"
        except asyncio.TimeoutError:
            return False # Connection failed

        return True # Connection successful

    async def __connect_answer(self) -> bool:
        """Function to connect as answer"""
        pc = RTCPeerConnection(configuration=ICE_CONFIG)
        self.peer_connection = pc
        self.__set_peer_connection_events(pc)

        dc = None

        @pc.on('datachannel')
        async def on_datachannel(data_channel):
            """When data channel received and opened sets is_p2p_connected event"""
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
        print(f"Received offer: {data}")

        if data.type != "share_offer_request":
            raise IncorrectRequestTypeError("Request is not share_offer.")

        offer = data.content

        offer = RTCSessionDescription(sdp=offer["sdp"], type="offer")
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        answer = Request(
            request_type="share_answer_request",
            content={"sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type}
        )

        await self.websocket.send(answer.json_string)
        print(f"Answer sent: {answer.json_string}")

        try:
            await asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            self.data_channel = dc
            # self.p2p_connection_state = "connected"
        except asyncio.TimeoutError:
            return False # Connection failed

        return True # Connection successful

    async def __establish_p2p_connection(self, role: str) -> RTCDataChannel | None:
        """Runs conenct function depending on user's role"""
        match role:
            case "offer":
                self.role = "offer"
                is_p2p_connected = await self.__connect_offer()
            case "answer":
                self.role = "answer"
                is_p2p_connected = await self.__connect_answer()
            case _:
                raise ValueError("Incorrect role.")

        if is_p2p_connected:
            self.is_p2p_connected.set()
            self.p2p_connection_state = "connected"

        return is_p2p_connected

    async def __wait_for_connection_request(self):
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

        connection_request = Request.from_string(connection_request)
        role = connection_request.content["role"]
        answer_connection_request = Request(
            request_type="connect_to_request",
            user_id=self.user_id,
            content={"role": "answer", "target_user_id": self.target_user_id}
        )
        await self.websocket.send(answer_connection_request.json_string)
        print(f"Connect to request sent: {answer_connection_request}")
        await self.__establish_p2p_connection(role)

    async def connect_to_server(self):
        """
        Connects user to the server by sending register_request
        and waits in case connection request received
        """
        websocket = await websockets.connect(SERVER_URL)
        self.websocket = websocket

        register_request = Request(
            request_type="register_request",
            user_id=self.user_id
        )

        await websocket.send(register_request.json_string)
        print(f"Register request sended: {register_request}")
        self.is_connected_websocket = True

        register_response = await websocket.recv()
        register_response = Request.from_string(register_response)
        print(f"Register response received: {register_response}")

        match register_response.type:
            case "connection_establishment_request":
                role = register_response.content["role"]
                await self.__establish_p2p_connection(role)
            case "wait_request":
                await self.__wait_for_connection_request()
            case _:
                raise IncorrectRequestTypeError("Incorrect response to register request")

    async def connect_to_peer(self) -> bool:
        """Tries to connect user to other peer"""
        self.p2p_connection_state = "connecting"

        connection_request = Request(
            request_type="connection_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id}
        )
        await self.websocket.send(connection_request.json_string)
        print(f"Connection request sent: {connection_request.json_string}")

        connection_response = await self.websocket.recv()
        connection_response = Request.from_string(connection_response)
        print(f"Connection response received: {connection_response}")

        if connection_response.type == "client_not_registered_error":
            raise UserNotRegisteredError("Target user is not registered on the server.")

        role = connection_response.content["role"]
        offer_connect_to_request = Request(
            request_type="connect_to_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id, "role": role}
        )
        await self.websocket.send(offer_connect_to_request.json_string)

        is_p2p_connected = await self.__establish_p2p_connection(role)

        if is_p2p_connected:
            # self.connection_type = "p2p_connection"
            self.is_p2p_connected.set()
            self.p2p_connection_state = "connected"
            return True # Connected successfully

        return False # Connection failed


    async def connect(self) -> bool:
        """Tries to connect user to the server and to other peer if not connected yet"""
        self.local_connection_initiated.set()

        if self.is_p2p_connected.is_set():
            return

        if not self.is_connected_websocket:
            await self.connect_to_server()

        await asyncio.sleep(0.05)

        if self.p2p_connection_state == "connecting":
            try:
                asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            except asyncio.TimeoutError:
                print("Connection timeout in connectio.connect()")
                self.is_p2p_connected = False
                self.p2p_connection_state = "disconnected"

        await self.connect_to_peer()


class Chat:
    """Class to represent chat between two users"""
    def __init__(self):
        user_id, target_user_id = self.__get_id()
        self.user_id = user_id
        self.target_user_id = target_user_id
        self.__message_queue = asyncio.Queue()
        self.__connection = Connection(self.user_id, self.target_user_id)

    @staticmethod
    def __get_id():
        """Get id of user and target user"""
        user_id = input("Enter your user ID: ").strip()
        target_user_id = input("Enter the ID of the user you want to connect to: ").strip()
        return user_id, target_user_id

    async def __message_loop(self):
        """Receives messages from user and adds them to the message queue"""
        print()
        while True:
            message = await ainput('You: ')
            if message:
                self.__message_queue.put_nowait(Message(
                                        message_type="message",
                                        content=message,
                                        sending_time=Time(),
                                        user_id=self.user_id,
                                        target_user_id=self.target_user_id
                                        ))

    async def __send_message_to_server(self, message: Message):
        relay_message_request = Request(
            request_type="relay_message_request",
            user_id=self.user_id,
            content={"message": message.json_string, "target_user": self.target_user_id}
        )
        await self.__connection.websocket.send(relay_message_request.json_string)
        print("Message was sent to the server")

    async def __send_message(self, message: Message):
        """
        Connects to otehr peer.
        If connection is already active or connection was successful
        sends message through open data channel
        """
        await self.__connection.connect()
        if self.__connection.is_p2p_connected.is_set() and self.__connection.p2p_connection_state == "connected":
            self.__connection.data_channel.send(message.json_string)
        elif self.__connection.is_connected_websocket:
            print(f"Is p2p connected: {self.__connection.is_p2p_connected.is_set()}, p2p connection state: {self.__connection.p2p_connection_state}")
            await self.__send_message_to_server(message)

    async def __send_message_loop(self):
        """If message queue is not empty gets message from it and sends it"""
        while True:
            message = await self.__message_queue.get()
            await self.__send_message(message)

    async def __close(self):
        """Closes chat and disconnects user"""
        self.__connection.local_disconnect_initialized = True
        await self.__connection.server_disconect()
        asyncio.create_task(self.__connection.p2p_disconnect())

    async def open(self):
        """Opens and runs chat"""
        try:
            message_task = asyncio.create_task(self.__message_loop())
            send_task = asyncio.create_task(self.__send_message_loop())
            connect_to_server_task = asyncio.create_task(self.__connection.connect_to_server())

            await asyncio.gather(connect_to_server_task, message_task, send_task)
        finally:
            await self.__close()


class Server:
    """Class to represent server which handles establishing connection between users"""
    SUPPORTED_REQUESTS = {"register_request", "connection_request", "connect_to_request", "relay_message_request"}

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.__clients: dict[User] = {}

    async def __connect_offer(self, websocket, target_user_id: str):
        """Receive oferer's SDP and send it to the target user"""
        target_user_websocket = self.__clients[target_user_id].websocket

        offer = await websocket.recv()
        print(f"Get offer: {offer}\n")
        await target_user_websocket.send(offer)

    async def __connect_answer(self, websocket, target_user_id: str):
        """Receive oferer's SDP and send it to the target user"""
        target_user_websocket = self.__clients[target_user_id].websocket

        answer = await websocket.recv()
        print(f"Get answer: {answer}\n")
        await target_user_websocket.send(answer)

    def __disconnect_user(self, user_id: str):
        """Disconnect user with given user id"""
        disconnected_user = self.__clients[user_id]
        if disconnected_user.pended_user_id:
            self.__clients[disconnected_user.pended_user_id].is_pended = False
            self.__clients[disconnected_user.pended_user_id].pending_user_id = None

            # Here messages which were not sent to target user
            # should be received from user as one request
            # and stored in the database

        self.__clients[user_id].disconnect()
        print(f"User {user_id} was disconnected")

    async def __handle_register_request(self, websocket, user_id: str):
        """Function which handles receiving and processing register_request from user"""
        client = self.__clients.setdefault(user_id, User())
        client.websocket = websocket
        client.is_online = True

        # Here stored messages should be sent to the user as one request
        # Messages should be ordered in some way

        target_user_id = self.__clients[user_id].pending_user_id

        if self.__clients[user_id].is_pended:
            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"user_id": self.__clients[user_id].pending_user_id, "role": "answer"}
            )
            await websocket.send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent: {connection_establishment_request.json_string}")
            self.__clients[user_id].role = "answer"

            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"user_id": user_id, "role": "offer"}
            )
            await self.__clients[target_user_id].websocket.send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent: {connection_establishment_request.json_string}")
            self.__clients[target_user_id].role = "offer"

            await self.__connect_answer(websocket, target_user_id)

        else:
            wait_request = Request(
            request_type="wait_request",
            )
            await websocket.send(wait_request.json_string)
            print(f"Wait request sent: {wait_request.json_string}")

    async def __handle_connection_request(self, websocket, user_id: str, data: dict):
        """Function which handles processing connection_request from user"""
        target_user_id = data["target_user_id"]

        if target_user_id not in self.__clients:
            error_request = Request(
                request_type="client_not_registered_error",
            )
            await websocket.send(error_request.json_string)

        elif self.__clients[target_user_id].is_online:
            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"user_id": user_id, "role": "answer"}
            )

            await self.__clients[target_user_id].websocket.send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent to answerer: {connection_establishment_request.json_string}")
            self.__clients[target_user_id].role = "answer"

            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"role": "offer"}
            )
            await websocket.send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent to offerer: {connection_establishment_request.json_string}")
            self.__clients[target_user_id].role = "offer"

        else:
            self.__clients[target_user_id].is_pended = True
            self.__clients[target_user_id].pending_user_id = user_id
            self.__clients[user_id].pended_user_id = target_user_id

    async def __handle_connect_to_request(self, websocket, data: dict):
        target_user_id = data["target_user_id"]
        role = data["role"]

        if role == "offer":
            await self.__connect_offer(websocket, target_user_id)
        elif role == "answer":
            await self.__connect_answer(websocket, target_user_id)

    async def __websocket_handler(self, websocket):
        print("New client connected.")
        try:
            async for request in websocket:
                request = Request.from_string(request)
                print(f"Request: {request.json_string}\n")
                request_type = request.type
                user_id = request.user_id
                data = request.content

                if request_type not in self.SUPPORTED_REQUESTS:
                    raise IncorrectRequestTypeError(f"Request with unsopported type ({request_type}) received")

                match request_type:
                    case "register_request":
                        await self.__handle_register_request(websocket, user_id)
                    case "connection_request":
                        await self.__handle_connection_request(websocket, user_id, data)
                    case "connect_to_request":
                        await self.__handle_connect_to_request(websocket, data)
                    case "relay_message_request":
                        pass

        except websockets.exceptions.ConnectionClosed:
            print(f"Connection closed for user: {user_id}")
        finally:
            self.__disconnect_user(user_id)
            await websocket.close()

    async def run(self):
        """Runs websocket server"""
        async with websockets.serve(self.__websocket_handler, self.ip, self.port):
            print(f"WebSocket server is running on ws://{self.ip}:{self.port}")
            await asyncio.Future()
