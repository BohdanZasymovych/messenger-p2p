"""objects for messenger.py and server.py"""
import json
import os
import asyncio
import logging
from datetime import datetime
from typing import Union
import uuid
from aioconsole import ainput
from aiortc import (RTCPeerConnection,
                    RTCSessionDescription,
                    RTCDataChannel,
                    RTCConfiguration,
                    RTCIceServer)
import websockets
import asyncpg
from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.server import WebSocketServerProtocol


WebSocket = Union[WebSocketClientProtocol, WebSocketServerProtocol]



# Ensure folder for logs exists
FOLDER_PATH = "./logs"
if not os.path.exists(FOLDER_PATH):
    os.makedirs(FOLDER_PATH)

# Set up logging
TIMESTAMP = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
LOG_FILENAME = f"./logs/log_{TIMESTAMP}.log"
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


ICE_CONFIG = RTCConfiguration(
    iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
)

# SERVER_URL = "ws://0.0.0.0:8000"
SERVER_URL = "ws://messenger_server:8000"

MESSAGE_NAMESPACE = uuid.UUID("1bc43a13-70f6-49c3-bea7-26f4fcc5b6c8")

DATABASE_URL = os.getenv("DATABASE_URL")


async def save_message_to_db(user_id: str, target_user_id: str, content: str) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""--sql
            INSERT INTO messages (user_id, target_user_id, content)
            VALUES ($1, $2, $3);
        """, user_id, target_user_id, content)
        print(f"Message from {user_id} to {target_user_id} saved to database.")
    finally:
        await conn.close()


async def get_messages_from_db(user_id: str, target_user_id: str) -> list:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("""--sql
            SELECT content FROM messages
            WHERE user_id = $1 AND target_user_id = $2;
        """, target_user_id, user_id)

        await conn.execute("""--sql
            DELETE FROM messages
            WHERE user_id = $1 AND target_user_id = $2;
        """, target_user_id, user_id)

        messages = [row['content'] for row in rows]

        return messages
    finally:
        await conn.close()


class IncorrectRequestTypeError(Exception):
    """Exception which is raised when request with incorrect type is received"""


class ConnectionTimeoutError(Exception):
    """Exception which is raised when connection is not established within certain amount of time"""


class UserNotRegisteredError(Exception):
    """Exception which is raised when target user is not registered on server"""


class User:
    """Class that represents user on the server side"""
    def __init__(self, websocket=None):
        self.is_online = False # Indicates if user is connected to the server
        self.role = None
        self.is_pended = False # Indicates if someone is waiting for user
        self.pending_user_id = None # User waiting for you
        self.pended_user_id = None # User you are waiting for
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
    
    def __repr__(self):
        return (f"User(is_online={self.is_online}, role={self.role!r}, is_pended={self.is_pended}, "
                f"pending_user_id={self.pending_user_id!r}, pended_user_id={self.pended_user_id!r}, "
                f"connection_type={self.connection_type!r})")


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
        """Returns string representation of the time to the seconds"""
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

    @property
    def unique_id(self):
        """Returns unique id of the message based on hash"""
        message_info = f"""{self.content}|{self.sending_time.date}
|{self.sending_time.time}|{self.user_id}|{self.target_user_id}"""

        return str(uuid.uuid5(MESSAGE_NAMESPACE, message_info))

    def __str__(self):
        return f"User {self.user_id} ({self.sending_time}): {self.content}"


class Request:
    """Class to represent request to the server or from it"""
    def __init__(self, request_type: str, user_id: str=None, content: dict=None):
        self.type: str = request_type
        self.user_id: str = user_id # id of user who had sent request, if server had sent should be None
        self.content: dict = content if content is not None else {}

    @property
    def json_string(self) -> str:
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

    def __str__(self) -> str:
        """Returns string representation of the request"""
        return self.json_string


class Connection:
    """Class to represent connection between to users"""
    def __init__(self, user_id: str, target_user_id: str):
        self.user_id: str = user_id
        self.target_user_id: str = target_user_id

        self.peer_connection: RTCPeerConnection | None = None
        self.data_channel: RTCDataChannel | None = None
        self.websocket: WebSocket | None = None

        self.connection_type: str = "disconnected"
        self.is_connected_websocket: bool = False
        self.is_p2p_connected: asyncio.Event = asyncio.Event()
        self.p2p_connection_state: str = "disconnected"
        self.is_target_user_online: bool | None = None
        self.is_p2p_connection_failed: bool = False

        self.role: str | None = None

        self.local_connection_initiated: asyncio.Event = asyncio.Event()
        self.local_disconnect_initialized: bool = False
        self.data_channel_opening_event: asyncio.Event = asyncio.Event()
        self.data_channel_closing_event: asyncio.Event = asyncio.Event()

        self.__receive_server_requests_task: asyncio.Task | None = None
        self.__handle_server_requests_task: asyncio.Task | None = None
        # self.__ping_request_task: asyncio.Task | None = None
        self.__establish_p2p_connection_task: asyncio.Task | None = None


        self.received_messages_queue: asyncio.Queue = asyncio.Queue()
        self.requests_queue: asyncio.Queue = asyncio.Queue()

        self.futures: dict[str, asyncio.Future] = {}

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
        self.connection_type = "disconnected"
        self.peer_connection = None
        self.data_channel = None
        self.is_p2p_connected.clear()
        self.is_p2p_connection_failed = False
        self.role = None

    async def server_disconect(self):
        """Disconnects user from the server"""
        if self.websocket:
            await self.__cancel_server_listener_task()
            await self.websocket.close()

        self.is_connected_websocket = False
        self.websocket = None

        await self.p2p_disconnect()

    async def __on_disconnect(self) -> None:
        """
        Waits untill data channel was closed, clears user
        and, if disconnect was initialized by another peer,
        launches function waiting for connection request
        """
        while True:
            await self.data_channel_closing_event.wait()
            self.data_channel_closing_event.clear()
            await self.p2p_disconnect()

            if self.local_disconnect_initialized:
                continue

            self.local_disconnect_initialized = False
            self.is_target_user_online = None
            print("Websocket was closed")

    def __receive_message(self, message: str) -> None:
        """Adds message received as json string to the queue"""
        self.received_messages_queue.put_nowait(message)

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
            self.__receive_message(message)

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
            content={"target_user_id": self.target_user_id,
                    "offer": {"type": pc.localDescription.type,
                    "sdp": pc.localDescription.sdp}}
        )
        answer = asyncio.Future() # share_answer_request
        self.futures["share_answer_request"] = answer
        await self.websocket.send(offer_request.json_string)
        print(f"Offer sent: {offer_request}")

        print("Waiting for answer...")
        answer = await answer
        del self.futures["share_answer_request"]

        answer = answer.content["answer"]
        answer = RTCSessionDescription(sdp=answer["sdp"], type="answer")
        await pc.setRemoteDescription(answer)

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

        print("Waiting for offer...")
        offer = asyncio.Future() # share_offer_request
        self.futures["share_offer_request"] = offer
        offer = await offer
        del self.futures["share_offer_request"]

        offer = offer.content["offer"]
        offer = RTCSessionDescription(sdp=offer["sdp"], type="offer")
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        answer = Request(
            request_type="share_answer_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id,
                    "answer": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}}
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

    async def __establish_server_connection(self) -> None:
        """
        Function which establishes connection to the server
        by sending server_connection_request
        and waiting for it from another peer
        """
        await self.__update_target_user_status()
        if self.is_target_user_online is False:
            self.connection_type = "disconnected"
            return False

        server_connection_request = Request(
            request_type="server_connection_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id}
        )
        server_connection_response = asyncio.Future()
        self.futures["server_connection_request"] = server_connection_response
        await self.websocket.send(server_connection_request.json_string)

        try:
            server_connection_response = await asyncio.wait_for(server_connection_response, 12)
        except asyncio.TimeoutError:
            self.connection_type = "disconnected"
            return False # Connection failed

        del self.futures["server_connection_request"]

        # server_connection_response = Request.from_string(server_connection_response)
        if server_connection_response.type == "server_connection_request":
            self.connection_type = "server_connection"
            return True

        raise IncorrectRequestTypeError("Incorrect response to server connection request")

    async def __establish_p2p_connection(self) -> bool:
        """Runs connect function depending on user's role"""
        self.p2p_connection_state = "connecting"
        match self.role:
            case "offer":
                self.role = "offer"
                is_p2p_connected = await self.__connect_offer()
            case "answer":
                self.role = "answer"
                is_p2p_connected = await self.__connect_answer()
            case _:
                raise ValueError("Incorrect role.")

        # is_p2p_connected = False ### For testing failing p2p connection
        if is_p2p_connected:
            self.is_p2p_connected.set()
            self.p2p_connection_state = "connected"
            self.connection_type = "p2p_connection"
            self.is_target_user_online = True
        else:
            self.is_p2p_connection_failed = True
            await self.__establish_server_connection()

        return is_p2p_connected

    async def __receive_server_requests(self):
        """Function which receives requests from server and adds them to the requests queue"""
        try:
            async for request in self.websocket:
                print(f"Request received: {request}")
                self.requests_queue.put_nowait(request)
        except websockets.exceptions.ConnectionClosed:
            print("Websocket was closed")
            await self.server_disconect()
            return
        except asyncio.CancelledError:
            print("Handler task was cancelled")
            return

    async def __handle_server_requests(self) -> None:
        try:
            while True:
                request = await self.requests_queue.get()
                request = Request.from_string(request)
                request_type = request.type

                if request_type == "relay_message_request":
                    self.__receive_message(request.content["message"])

                elif request_type == "connection_establishment_request":
                    self.role = request.content["role"]
                    self.__establish_p2p_connection_task = asyncio.create_task(self.__establish_p2p_connection())

                # elif request_type == "ping_request":
                #     print("Ping request received")

                elif request_type in self.futures:
                    self.futures[request_type].set_result(request)

                else:
                    raise IncorrectRequestTypeError("Incorrect request type in __handle_server_requests.")

        except asyncio.CancelledError:
            print("Handler task was cancelled")
            return

    async def __cancel_server_listener_task(self):
        """Cancels handle server requests task"""
        if self.__handle_server_requests_task is not None:
            self.__handle_server_requests_task.cancel()
            try:
                await self.__handle_server_requests_task
            except asyncio.CancelledError:
                self.__handle_server_requests_task = None

        if self.__receive_server_requests_task is not None:
            self.__receive_server_requests_task.cancel()
            try:
                await self.__receive_server_requests_task
            except asyncio.CancelledError:
                self.__receive_server_requests_task = None

    # async def __ping_server(self):
    #     while True:
    #         ping_request = Request(
    #             request_type="ping_request",
    #             user_id=self.user_id,
    #             content={}
    #         )
    #         await self.websocket.send(ping_request.json_string)
    #         await asyncio.sleep(1)

    async def __update_target_user_status(self):
        """Updates target user status (online, offline) by sending get_target_user_status_request"""
        get_target_user_status_request = Request(
            request_type="get_target_user_status_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id}
        )
        target_user_status_response = asyncio.Future()
        self.futures["target_user_status_response"] = target_user_status_response
        await self.websocket.send(get_target_user_status_request.json_string)

        target_user_status_response = await target_user_status_response
        del self.futures["target_user_status_response"]

        print(f"Target user status response received: {target_user_status_response}")
        self.is_target_user_online = target_user_status_response.content["target_user_status"]


    async def connect_to_server(self):
        """
        Connects user to the server by sending register_request
        and waits in case connection request received
        """
        if self.websocket is None:
            websocket = await websockets.connect(SERVER_URL)
            self.websocket = websocket
            self.is_connected_websocket = True
            self.__handle_server_requests_task = asyncio.create_task(self.__handle_server_requests())
            self.__receive_server_requests_task = asyncio.create_task(self.__receive_server_requests())
            # self.__ping_request_task = asyncio.create_task(self.__ping_server())

        register_request = Request(
            request_type="register_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id}
        )
        register_response = asyncio.Future()
        self.futures["register_response"] = register_response
        await websocket.send(register_request.json_string)

        register_response = await register_response
        del self.futures["register_response"]

        match register_response.content["register_response_type"]:
            case "connection_establishment_request":
                self.role = register_response.content["role"]
                await self.__establish_p2p_connection()
            case "target_user_offline":
                self.is_target_user_online = False
            case "target_user_online":
                self.is_target_user_online = True
            case _:
                raise IncorrectRequestTypeError("Incorrect response to register request.")

    async def connect_to_peer(self) -> bool:
        """Tries to connect user to other peer"""
        connection_request = Request(
            request_type="connection_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id}
        )
        connection_response = asyncio.Future()
        self.futures["connection_response"] = connection_response
        await self.websocket.send(connection_request.json_string)
        # print(f"Connection request sent: {connection_request.json_string}")

        connection_response = await connection_response
        del self.futures["connection_response"]

        connection_response_type = connection_response.content["connection_response_type"]
        match connection_response_type:
            case "user_not_registered_error":
                raise UserNotRegisteredError("Target user is not registered on the server.")
            case "target_user_offline":
                self.is_target_user_online = False
                return False
            case "connection_establishment_request":
                self.is_target_user_online = True

        self.role = connection_response.content["role"]

        is_p2p_connected = await self.__establish_p2p_connection()

        if is_p2p_connected:
            self.is_p2p_connected.set()
            self.p2p_connection_state = "connected"
            self.is_p2p_connection_failed = False
            return True # Connected successfully

        self.p2p_connection_state = "disconnected"
        self.is_p2p_connection_failed = True
        return False # Connection failed

    async def connect(self) -> bool:
        """Tries to connect user to the server and to other peer if not connected yet"""
        self.local_connection_initiated.set()
        await asyncio.sleep(0.01)

        if self.is_p2p_connected.is_set():
            return

        if not self.is_connected_websocket:
            await self.connect_to_server()

        if self.connection_type == "server_connection":
            return

        if self.p2p_connection_state == "connecting":
            try:
                await asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            except asyncio.TimeoutError:
                print("Connection timeout in connection.connect().")
                self.is_p2p_connected = False
                self.p2p_connection_state = "disconnected"

        await self.connect_to_peer()


class Chat:
    """Class to represent chat between two users"""
    def __init__(self, user_id: str, target_user_id: str):
        self.user_id = user_id
        self.target_user_id = target_user_id
        self.__send_message_queue = asyncio.Queue()
        self.__connection = Connection(self.user_id, self.target_user_id)

    async def __on_message_received(self):
        while True:
            message = await self.__connection.received_messages_queue.get()
            message = Message.from_string(message)
            print(message)

    async def __message_loop(self):
        """Receives messages from user and adds them to the message queue"""
        print()
        while True:
            message = await ainput('You: ')
            if message:
                self.__send_message_queue.put_nowait(Message(
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
        Connects to other peer.
        If connection is already active or connection was successful
        sends message through open data channel
        """
        connection = self.__connection

        if connection.connection_type == "disconnected" and not connection.is_p2p_connection_failed:
            await connection.connect()

        if connection.is_p2p_connection_failed:
            await self.__send_message_to_server(message)
            return

        if connection.connection_type in ("disconnected", "server_connection"):
            await self.__send_message_to_server(message)
            return

        if connection.p2p_connection_state == "connected":
            connection.data_channel.send(message.json_string)
            return

        raise ValueError("Unexpected connection state.")

    async def __send_message_loop(self):
        """If message queue is not empty gets message from it and sends it"""
        while True:
            message = await self.__send_message_queue.get()
            await self.__send_message(message)

    async def __close(self):
        """Closes chat and disconnects user"""
        self.__connection.local_disconnect_initialized = True
        await self.__connection.server_disconect()
        asyncio.create_task(self.__connection.p2p_disconnect())

    async def open(self):
        """Opens and runs chat"""
        try:
            get_message_task = asyncio.create_task(self.__message_loop())
            send_message_task = asyncio.create_task(self.__send_message_loop())
            receive_message_task = asyncio.create_task(self.__on_message_received())
            connect_to_server_task = asyncio.create_task(self.__connection.connect_to_server())

            await asyncio.gather(connect_to_server_task, get_message_task, receive_message_task, send_message_task)
        finally:
            await self.__close()


class Server:
    """Class to represent server which handles establishing connection between users"""
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.__clients: dict[User] = {'1': User(), '2': User()} # user_id: User

    def __disconnect_user(self, user_id: str):
        """Disconnect user with given user id"""
        disconnected_user = self.__clients[user_id]
        if disconnected_user.pended_user_id:
            self.__clients[disconnected_user.pended_user_id].is_pended = False
            self.__clients[disconnected_user.pended_user_id].pending_user_id = None

            # Here messages which were not sent to the target user
            # should be received from user as one request
            # and stored in the database

        self.__clients[user_id].disconnect()
        print(f"User {user_id} was disconnected")

    async def __handle_register_request(self, websocket, user_id: str, data: dict):
        """Function which handles receiving and processing register_request from user"""
        client = self.__clients.setdefault(user_id, User())
        client.websocket = websocket
        client.is_online = True

        target_user_id = data["target_user_id"]

        # Stored messages are sent to the user as one relay_message_request
        stored_messages = await get_messages_from_db(user_id, target_user_id)
        for message in stored_messages:
            # message = Message.from_string(message)
            relay_message_request = Request(
                request_type="relay_message_request",
                content={"message": message}
            )
            await websocket.send(relay_message_request.json_string)

        if self.__clients[user_id].is_pended:
            target_user_id = self.__clients[user_id].pending_user_id

            self.__clients[user_id].is_pended = False
            self.__clients[user_id].pending_user_id = None
            self.__clients[target_user_id].pended_user_id = None

            register_response = Request(
                request_type="register_response",
                content={"register_response_type": "connection_establishment_request",
                        "user_id": self.__clients[user_id].pending_user_id, "role": "answer"}
            )
            await websocket.send(register_response.json_string)
            print(f"Connection establishment request sent: {register_response.json_string}")
            self.__clients[user_id].role = "answer"

            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"user_id": user_id, "role": "offer"}
            )
            await self.__clients[target_user_id].websocket.send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent: {connection_establishment_request.json_string}")
            self.__clients[target_user_id].role = "offer"

        elif self.__clients[target_user_id].is_online:
            register_response = Request(
                request_type="register_response",
                content = {"register_response_type": "target_user_online"}
            )
            await websocket.send(register_response.json_string)

        else:
            register_response = Request(
                request_type="register_response",
                content = {"register_response_type": "target_user_offline"}
            )
            await websocket.send(register_response.json_string)

    async def __handle_connection_request(self, websocket, user_id: str, data: dict):
        """Function which handles processing connection_request from user"""
        target_user_id = data["target_user_id"]

        if target_user_id not in self.__clients:
            connection_response= Request(
                request_type="connection_response",
                content = {"connection_response_type": "client_not_registered_error"}
            )
            await websocket.send(connection_response.json_string)

        elif self.__clients[target_user_id].is_online:
            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"user_id": user_id, "role": "answer"}
            )

            await self.__clients[target_user_id].websocket.send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent to answerer: {connection_establishment_request}")
            self.__clients[target_user_id].role = "answer"

            connection_response = Request(
                request_type="connection_response",
                content={"connection_response_type": "connection_establishment_request", "role": "offer"}
            )
            await websocket.send(connection_response.json_string)
            print(f"Connection establishment request sent to offerer: {connection_response}")
            self.__clients[target_user_id].role = "offer"

        else:
            self.__clients[target_user_id].is_pended = True
            self.__clients[target_user_id].pending_user_id = user_id
            self.__clients[user_id].pended_user_id = target_user_id

            connection_response = Request(
                request_type="connection_response",
                content = {"connection_response_type": "target_user_offline"}
            )
            await websocket.send(connection_response.json_string)

    async def __handle_share_offer_request(self, data: dict):
        """Sends offer SDP to the target user"""
        target_user_id = data["target_user_id"]
        target_user_websocket = self.__clients[target_user_id].websocket
        offer = data["offer"]
        share_offer_request = Request(
            request_type="share_offer_request",
            content={"user_id": target_user_id, "offer": offer}
        )

        await target_user_websocket.send(share_offer_request.json_string)
        print(f"Offer was sent to the target user: {share_offer_request.json_string}")

    async def __handle_share_answer_request(self, data: dict):
        """Sends answer SDP to the target user"""
        target_user_id = data["target_user_id"]
        target_user_websocket = self.__clients[target_user_id].websocket
        answer = data["answer"]
        share_answer_request = Request(
            request_type="share_answer_request",
            content={"user_id": target_user_id, "answer": answer}
        )

        await target_user_websocket.send(share_answer_request.json_string)
        print(f"Answer was sent to the target user: {share_answer_request.json_string}")

    async def __handle_relay_message_request(self, user_id: str, data: dict):
        """
        Function which handles processing relay_message_request from user
        If user onlines sends message to the target user
        If user is offline stores message in the database
        """
        target_user_id = data["target_user"]
        if self.__clients[target_user_id].is_online:
            target_user_websocket = self.__clients[target_user_id].websocket
            relay_message_request = Request(
                request_type="relay_message_request",
                content={"message": [data["message"]]}
                )
            await target_user_websocket.send(relay_message_request.json_string)
            print(f"Message from {user_id} to {target_user_id} was relayed.")

        else:
            try:
                await save_message_to_db(
                    user_id=user_id,
                    target_user_id=target_user_id,
                    content=data["message"]
                )
                print(f"Message from {user_id} to {data['target_user']} saved to database.")

            except KeyError as e:
                print(f"Missing key in relay_message_request: {e}")
            except Exception as e:
                print(f"Error while handling relay_message_request: {e}")

    async def __handle_server_connection_request(self, data: dict):
        target_user_id = data["target_user_id"]
        target_user_websocket = self.__clients[target_user_id].websocket
        server_connection_request = Request(
            request_type="server_connection_request",
            content={"target_user_id": target_user_id}
        )
        await target_user_websocket.send(server_connection_request.json_string)

    async def __handle_get_target_user_status_request(self, user_id: str, data: dict):
        target_user_id = data["target_user_id"]
        websocket = self.__clients[user_id].websocket

        target_user_status_request = Request(
            request_type="target_user_status_response",
            content={"target_user_status": self.__clients[target_user_id].is_online}
        )
        await websocket.send(target_user_status_request.json_string)
        print(f"Target user status request sent: {target_user_status_request.json_string}")

    async def __websocket_handler(self, websocket):
        print("New client connected.")
        try:
            async for request in websocket:
                request = Request.from_string(request)
                print(f"Request: {request.json_string}\n")
                request_type = request.type
                user_id = request.user_id
                data = request.content

                match request_type:
                    case "register_request":
                        await self.__handle_register_request(websocket, user_id, data)
                    case "connection_request":
                        await self.__handle_connection_request(websocket, user_id, data)
                    case "share_offer_request":
                        await self.__handle_share_offer_request(data)
                    case "share_answer_request":
                        await self.__handle_share_answer_request(data)
                    case "server_connection_request":
                        await self.__handle_server_connection_request(data)
                    case "relay_message_request":
                        await self.__handle_relay_message_request(user_id, data)
                    case "get_target_user_status_request":
                        await self.__handle_get_target_user_status_request(user_id, data)
                    # case "ping_request":
                    #     print("Ping request received")
                    #     pong_response = Request(
                    #         request_type="ping_request",
                    #         content={}
                    #     )
                    #     await websocket.send(pong_response.json_string)
                    case _:
                        raise IncorrectRequestTypeError(f"Incorrect request type in __websocket_handler ({request_type}).")

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
