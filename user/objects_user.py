"""objects related to the user"""
import os

os.environ['AIORTC_MIN_PORT'] = '40000'
os.environ['AIORTC_MAX_PORT'] = '40100'

import logging
from datetime import datetime
import asyncio
from typing import Union
# from aioconsole import ainput
from aiortc import (RTCPeerConnection,
                    RTCSessionDescription,
                    RTCDataChannel,
                    RTCConfiguration,
                    RTCIceServer)

import websockets
import asyncpg
from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.server import WebSocketServerProtocol

from messages_requests import Request, Message, Encryption
WebSocket = Union[WebSocketClientProtocol, WebSocketServerProtocol]

from fastapi import FastAPI, HTTPException, APIRouter, Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import threading


def setup_logging():
    """Sets up logging for the application"""
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
setup_logging()

ICE_SERVERS = [
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
        RTCIceServer(urls=["stun:stun2.l.google.com:19302"])
]

ICE_CONFIG = RTCConfiguration(
    iceServers=ICE_SERVERS
)

class IncorrectRequestTypeError(Exception):
    """Exception which is raised when request with incorrect type is received"""


class ConnectionTimeoutError(Exception):
    """Exception which is raised when connection is not established within certain amount of time"""


class UserNotRegisteredError(Exception):
    """Exception which is raised when target user is not registered on server"""


class Connection:
    """Class to represent connection between to users"""
    SERVER_URL = "ws://messenger_server:9000"

    def __init__(self, user_id: str, target_user_id: str):
        self.user_id: str = user_id
        self.target_user_id: str = target_user_id

        self.peer_connection: RTCPeerConnection | None = None
        self.data_channel: RTCDataChannel | None = None
        self.__websocket: WebSocket | None = None

        # self.connection_type: str = "disconnected"
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

    @property
    def websocket(self) -> WebSocket:
        """Returns websocket object"""
        return self.__websocket

    @websocket.setter
    def websocket(self, websocket: WebSocket):
        """Sets websocket object and sets is_online to True"""
        print("Setter triggered")
        self.__websocket = websocket
        self.is_online = True
        self.__handle_server_requests_task = asyncio.create_task(self.__handle_server_requests())
        self.__receive_server_requests_task = asyncio.create_task(self.__receive_server_requests())

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
        # self.connection_type = "disconnected"
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

    def __receive_message(self, message: str, encryption: str, public_key=None) -> None:
        """Adds message received as json string to the queue"""
        self.received_messages_queue.put_nowait({"message": message, "encryption": encryption, "public_key": public_key})

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
            self.__receive_message(message, encryption="none")

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
            # self.connection_type = "p2p_connection"
            self.is_target_user_online = True

        return is_p2p_connected

    def __receive_stored_messages(self, messages: list[str]) -> None:
        """Adds messages received as json string to the queue"""
        for message in messages:
            self.__receive_message(message, encryption="long_term_public_key")

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
                    self.__receive_message(request.content["message"], encryption="public_key", public_key=request.content["public_key"])

                elif request_type == "send_stored_messages":
                    self.__receive_stored_messages(request.content["message"])

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

    async def connect_to_server(self, public_key: str) -> None:
        """
        Connects user to the server by sending register_request
        and waits in case connection request received
        """
        if self.websocket is None:
            websocket = await websockets.connect(self.SERVER_URL)
            self.websocket = websocket

        register_request = Request(
            request_type="register_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id,
                    "public_key": public_key}
        )
        register_response = asyncio.Future()
        self.futures["register_response"] = register_response
        await self.websocket.send(register_request.json_string)

        register_response = await register_response
        del self.futures["register_response"]

        match register_response.content["register_response_type"]:
            case "connection_establishment_request":
                self.role = register_response.content["role"]
                peer_public_key = register_response.content["public_key"]
                await self.__establish_p2p_connection()
            case "target_user_offline":
                self.is_target_user_online = False
                return
            case "target_user_online":
                self.is_target_user_online = True
                peer_public_key = register_response.content["public_key"]
                return peer_public_key
            case _:
                raise IncorrectRequestTypeError("Incorrect response to register request.")
        return peer_public_key

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
                return
            case "connection_establishment_request":
                peer_public_key = connection_response.content["public_key"]
                self.is_target_user_online = True

        self.role = connection_response.content["role"]

        is_p2p_connected = await self.__establish_p2p_connection()

        if is_p2p_connected:
            self.is_p2p_connected.set()
            self.p2p_connection_state = "connected"
            self.is_p2p_connection_failed = False
            # return True # Connected successfully
            return peer_public_key

        self.is_p2p_connection_failed = True
        self.p2p_connection_state = "disconnected"
        # return False # Connection failed
        return peer_public_key

    async def connect(self, public_key: str) -> bool:
        """Tries to connect user to the server and to other peer if not connected yet"""
        self.local_connection_initiated.set()
        await asyncio.sleep(0.01)

        await self.__update_target_user_status()

        if self.is_p2p_connected.is_set() or self.is_p2p_connection_failed:
            return

        if not self.is_connected_websocket:
            await self.connect_to_server(public_key)

        if self.p2p_connection_state == "connecting":
            try:
                await asyncio.wait_for(self.is_p2p_connected.wait(), 10)
            except asyncio.TimeoutError:
                print("Connection timeout in connection.connect().")
                self.is_p2p_connected.clear()
                self.p2p_connection_state = "disconnected"

        public_key = await self.connect_to_peer()
        return public_key


class Chat:
    """Class to represent chat between two users"""
    DATABASE_URL = os.getenv("DATABASE_URL_CLIENT")


    def __init__(self, user_id: str, target_user_id: str, on_message_callback: callable=None):
        self.user_id = user_id
        self.target_user_id = target_user_id
        self.__on_message_callback: callable = on_message_callback
        self.__send_message_queue = asyncio.Queue()
        self.__connection = Connection(self.user_id, self.target_user_id)

        self.__encryption = Encryption()
        self.__encryption.generate_keys()
        print(f"Public key: {self.__encryption.public_key}")

        self.__long_term_encryptinon = Encryption()
        self.__long_term_encryptinon.load_long_term_keys()
        print(f"Long term public key: {self.__long_term_encryptinon.public_key}")

        self.is_opened = asyncio.Event()

    async def __save_message_to_db(self, message: Message, is_outgoing: bool = True) -> None:
        """Saves message to the database"""
        try:
            user_id = message.user_id
            target_user_id = message.target_user_id
            message_content = message.content

            print(f"Saving message to database: {user_id} -> {target_user_id}: '{message_content[:20]}...'")
            
            conn = await asyncpg.connect(self.DATABASE_URL)
            try:
                await conn.execute("""--sql
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        target_user_id TEXT NOT NULL,
                        message TEXT NOT NULL,
                        is_outgoing BOOLEAN DEFAULT TRUE,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                await conn.execute("""--sql
                    INSERT INTO messages (user_id, target_user_id, message, is_outgoing)
                    VALUES ($1, $2, $3, $4);
                """, user_id, target_user_id, message_content, is_outgoing)
                
                print(f"Message from {user_id} to {target_user_id} saved to database")
            finally:
                await conn.close()
        except Exception as e:
            print(f"Error saving message to database: {str(e)}")

    async def __get_messages_from_db(self, limit=100) -> list:
        """Gets messages between current user and target user from the database"""
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            try:
                await conn.execute("""--sql
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        target_user_id TEXT NOT NULL,
                        message TEXT NOT NULL,
                        is_outgoing BOOLEAN DEFAULT TRUE,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                rows = await conn.fetch("""--sql
                    SELECT * FROM messages
                    WHERE (user_id = $1 AND target_user_id = $2) 
                    OR (user_id = $2 AND target_user_id = $1)
                    ORDER BY timestamp ASC
                    LIMIT $3;
                """, self.user_id, self.target_user_id, limit)

                print(f"Retrieved {len(rows)} messages from database for chat between {self.user_id} and {self.target_user_id}")
                
                messages = []
                for row in rows:
                    is_from_me = row["user_id"] == self.user_id
                    
                    messages.append({
                        "sender": "me" if is_from_me else "you",
                        "text": row["message"],
                        "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"])
                    })
                
                return messages
            finally:
                await conn.close()
        except Exception as e:
            print(f"Error retrieving messages from database: {str(e)}")
            return []

    async def get_message_history(self):
        """Public method to get message history from database"""
        return await self.__get_messages_from_db()

    async def __on_message_received(self):
        while True:
            message = await self.__connection.received_messages_queue.get()
            encryption = message["encryption"]
            if message["public_key"] is not None:
                self.__encryption.set_peer_public_key(message["public_key"])
        
            if encryption == "long_term_public_key":
                message = self.__long_term_encryptinon.decrypt(message["message"])
            elif encryption == "public_key":
                message = self.__encryption.decrypt(message["message"])
            else:
                message = message["message"]

            message_obj = Message.from_string(message)
            
            await self.__save_message_to_db(message_obj, is_outgoing=False)
    
            if self.__on_message_callback:
                self.__on_message_callback(message_obj, self.target_user_id)
            
            print(f"Message received and saved: {message_obj}")

    # async def __on_message_received(self):
    #     while True:
    #         message = await self.__connection.received_messages_queue.get()
    #         encryption = message["encryption"]
    #         if message["public_key"] is not None:
    #             self.__encryption.set_peer_public_key(message["public_key"])
    
    #         if encryption == "long_term_public_key":
    #             message = self.__long_term_encryptinon.decrypt(message["message"])
    #         elif encryption == "public_key":
    #             message = self.__encryption.decrypt(message["message"])
    #         else:
    #             message = message["message"]

    #         message = Message.from_string(message)
    #         self.__on_message_callback(message, self.target_user_id) # Function from App class
    #         print(f"Message: {message}")

    async def __send_message_to_server(self, message: Message, encryption: str):
        message_json = message.json_string
        print(f"Encryption: {encryption}")
        if encryption == "long_term_public_key":
            encrypted_message = self.__long_term_encryptinon.encrypt(message_json)
        else:
            encrypted_message = self.__encryption.encrypt(message_json)

        relay_message_request = Request(
            request_type="relay_message_request",
            user_id=self.user_id,
            content={"message": encrypted_message, "target_user": self.target_user_id, "public_key": self.__encryption.public_key}
        )
        await self.__connection.websocket.send(relay_message_request.json_string)
        print("Message was sent to the server")

    async def __send_message_to_peer(self, message: Message):
        """
        Connects to other peer.
        If connection is already active or connection was successful
        sends message through open data channel
        """
        connection = self.__connection

        # Ensure connection is established
        public_key = await connection.connect(self.__encryption.public_key)
        print(f"Public key received: {public_key}")
        if public_key:
            self.__encryption.set_peer_public_key(public_key)

        if not connection.is_target_user_online:
            await self.__send_message_to_server(message, encryption="long_term_public_key")
            return

        if connection.is_p2p_connection_failed:
            await self.__send_message_to_server(message, encryption="public_key")
            return

        if connection.p2p_connection_state == "connected":
            connection.data_channel.send(message.json_string)
            return

        raise ValueError("Unexpected connection state.")

    async def __send_message_loop(self):
        """If message queue is not empty gets message from it and sends it"""
        while True:
            message = await self.__send_message_queue.get()
            await self.__send_message_to_peer(message)

    async def close(self):
        """Closes chat and disconnects user"""
        self.__connection.local_disconnect_initialized = True
        await self.__connection.server_disconect()
        asyncio.create_task(self.__connection.p2p_disconnect())

    async def open(self):
        """Opens and runs chat"""
        websocket = await websockets.connect(self.__connection.SERVER_URL)

        share_user_id_request = Request(
            request_type="share_user_id_request",
            user_id=self.user_id
        )
        await websocket.send(share_user_id_request.json_string)

        send_long_term_public_key_request = Request(
            request_type="send_long_term_public_key_request",
            user_id=self.user_id,
            content={"long_term_public_key": self.__long_term_encryptinon.public_key}
        )
        await websocket.send(send_long_term_public_key_request.json_string)

        get_long_term_public_key_request = Request(
            request_type="get_long_term_public_key_request",
            user_id=self.user_id,
            content={"target_user_id": self.target_user_id}
        )
        await websocket.send(get_long_term_public_key_request.json_string)
        long_term_public_key_response = await websocket.recv()
        long_term_public_key_response = Request.from_string(long_term_public_key_response)

        print(f"Long term public key response received: {long_term_public_key_response}")
        self.__long_term_encryptinon.set_peer_public_key(long_term_public_key_response.content["long_term_public_key"])

        self.__connection.websocket = websocket

        try:
            # get_message_task = asyncio.create_task(self.__message_loop())
            send_message_task = asyncio.create_task(self.__send_message_loop())
            receive_message_task = asyncio.create_task(self.__on_message_received())
            connect_to_server_task = asyncio.create_task(self.__connection.connect_to_server(self.__encryption.public_key))
            self.is_opened.set()

            await asyncio.gather(connect_to_server_task, receive_message_task, send_message_task)
        finally:
            await self.close()

    # async def __message_loop(self):
    #     """Receives messages from user and adds them to the message queue"""
    #     print()
    #     while True:
    #         message = await ainput('You: ')
    #         if message:
    #             message = Message(
    #                 message_type="message",
    #                 content=message,
    #                 user_id=self.user_id,
    #                 target_user_id=self.target_user_id
    #             )
    #             await self.__save_message_to_db(message)
    #             self.__send_message_queue.put_nowait(message)

    # def send_message(self, message: Message):
    #     """Sends message to the target user"""
    #     self.__send_message_queue.put_nowait(message)
    #     print(message)

    def send_message(self, message: str):
        """Sends message to the target user"""
        try:
            message_obj = Message(
                message_type="text",
                content=message,
                user_id=self.user_id,
                target_user_id=self.target_user_id
            )
            
            asyncio.create_task(self.__save_message_to_db(message_obj, is_outgoing=True))

            self.__send_message_queue.put_nowait(message_obj)
            
            print(f"Message queued for sending to {self.target_user_id}")
        except Exception as e:
            print(f"Error in send_message: {str(e)}")
            raise
    


class LoginRequest(BaseModel):
    user_id: str

class ChatRequest(BaseModel):
    user_id: str
    target_user_id: str

class MessageRequest(BaseModel):
    user_id: str
    target_user_id: str
    text: str
    timestamp: str


class App:
    """Class representing messenger application"""
    DATABASE_URL = os.getenv("DATABASE_URL_CLIENT")

    def __init__(self):
        # Create FastAPI instance
        self.api = FastAPI()
        self.user_id = None

        self.__chats_loaded = False
        
        # Create a separate router for API endpoints FIRST
        self.api_router = APIRouter(prefix="/api")
        
        self.__chats = {}  # user_id: Chat
        self.__messages = {}  # Format: {target_user_id: [messages]}
        
        # User ID event to signal when user ID is set
        self.__user_id_set = threading.Event()
        
        # Setup API routes BEFORE including router
        self.__setup_api_routes()
        
        # Include the API router in the app
        self.api.include_router(self.api_router)
        
        # Add CORS middleware
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add root redirect
        @self.api.get("/")
        def redirect_to_chat():
            return RedirectResponse(url="/chat.html")
        
        # Mount static files LAST - this ensures API routes take priority
        frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
        self.api.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


    def __setup_api_routes(self):
        """Setup API routes for the FastAPI application"""

        @self.api_router.post("/login")
        async def login(request: FastAPIRequest):
            try:
                data = await request.json()
                user_id = data.get("user_id")
                print(f"Login attempt with user_id: {user_id}")
                self.user_id = user_id
                self.__user_id_set.set()
                print("Login successful")
                return {"status": "success", "user_id": user_id}
            except Exception as e:
                print(f"Login error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.api_router.get("/get_messages/{user_id}/{target_user_id}")
        async def get_messages(user_id: str, target_user_id: str):
            """Get messages between user_id and target_user_id"""
            if user_id != self.user_id:
                print(f"User mismatch: {user_id} vs {self.user_id}")
                raise HTTPException(status_code=403, detail="Unauthorized access")

            if target_user_id in self.__chats:
                chat = self.__chats[target_user_id]
                return await chat.get_message_history()
            
            print(f"Chat with {target_user_id} not found in memory, checking database")
            
            temp_chat = Chat(
                user_id=self.user_id,
                target_user_id=target_user_id,
                on_message_callback=self.on_message_received
            )
            
            messages = await temp_chat.get_message_history()
            
            if messages and len(messages) > 0:
                print(f"Found {len(messages)} messages in database, creating chat")
                await self.add_chat(target_user_id)
                return messages
            print(f"No messages found for chat with {target_user_id}")
            return []

        @self.api_router.post("/send_message")
        async def send_message(msg: MessageRequest):
            try:
                # Validate the user
                if msg.user_id != self.user_id:
                    raise HTTPException(status_code=403, detail="Unauthorized access")
                
                # Store outgoing message in memory
                message_entry = {
                    "sender": "me",
                    "text": msg.text,
                    "timestamp": msg.timestamp
                }

                if msg.target_user_id not in self.__messages:
                    self.__messages[msg.target_user_id] = []
                self.__messages[msg.target_user_id].append(message_entry)

                if msg.target_user_id not in self.__chats:
                    print(f"Creating chat with {msg.target_user_id} for sending message")
                    await self.add_chat(msg.target_user_id)

                self.send_message(msg.target_user_id, msg.text)

                return {"status": "sent"}
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.api_router.get("/users")
        async def get_users():
            # Return list of all users with whom the current user has chats
            return list(self.__chats.keys())

        @self.api_router.get("/chats_loaded")
        async def chats_loaded():
            return {"loaded": self.__chats_loaded}

        @self.api_router.get("/get_chats/{user_id}")
        async def get_chats(user_id: str):
            # Validate if the requested user_id matches the app's user_id
            if user_id != self.user_id:
                raise HTTPException(status_code=403, detail="Unauthorized access")

            # Return all chat users for the current user
            # chats = [id for id, chat in self.__chats.items() if chat.user_id != user_id]
            return list(self.__chats.keys())

        @self.api_router.post("/add_chat")
        async def add_chat(data: ChatRequest):
            try:
                # Validate the user
                if data.user_id != self.user_id:
                    raise HTTPException(status_code=403, detail="Unauthorized access")
                
                # Add chat using the existing method
                await self.add_chat(data.target_user_id)
                return {"status": "chat added"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    async def add_chat(self, target_user_id: str):
        """Adds chat with the target user to application"""
        # Create chat with the callback to receive messages
        chat = Chat(
            self.user_id, 
            target_user_id,
            on_message_callback=self.on_message_received
        )
        self.__chats[target_user_id] = chat

        # add chat to the database
        conn = await asyncpg.connect(self.DATABASE_URL)
        try:
            await conn.execute("""--sql
                INSERT INTO chats (target_user_id)
                VALUES ($1)
                ON CONFLICT (target_user_id) DO NOTHING;
                """, target_user_id)
        finally:
            await conn.close()

        # Start chat in a background task so it doesn't block
        asyncio.create_task(chat.open())

    async def remove_chat(self, target_user_id: str):
        """Removes chat with the target user from application"""
        if target_user_id not in self.__chats:
            return

        chat = self.__chats[target_user_id]
        await chat.close()  # Close the chat connection
        del self.__chats[target_user_id]

        # remove chat from the database
        conn = await asyncpg.connect(self.DATABASE_URL)
        try:
            await conn.execute("""--sql
                DELETE FROM chats WHERE target_user_id = $1;
                """, target_user_id)
        finally:
            await conn.close()

    async def __get_chats_from_db(self) -> list[str]:
        """Gets chats from database"""
        print("Getting chats from database")
        conn = await asyncpg.connect(self.DATABASE_URL)

        try:
            chats = await conn.fetch("""--sql
                SELECT * FROM chats;
                """)
        finally:
            await conn.close()

        print(f"Chats from database: {chats}")
        return [chat["target_user_id"] for chat in chats]
    
    def send_message(self, target_user_id: str, message: str):
        """Sends message to the target user"""
        if target_user_id in self.__chats:
            chat = self.__chats[target_user_id]
            chat.send_message(message)
            print(f"Message sent to {target_user_id}")
        else:
            raise ValueError(f"Chat with {target_user_id} not found.")

    def on_message_received(self, message: Message, target_user_id: str):
        """Function which is called when message is received"""
        message_text = message.content  # Get text of the message (str)

        # Create message entry
        message_entry = {
            "sender": "them",  # Message is from the other user
            "text": message_text,
            "timestamp": datetime.now().isoformat()
        }

        # Store message in memory
        if target_user_id not in self.__messages:
            self.__messages[target_user_id] = []
        self.__messages[target_user_id].append(message_entry)

        print(f"Received message from {target_user_id}: {message_text}")

    async def open(self):
        # Start the API server
        def start_server():
            uvicorn.run(self.api, host="0.0.0.0", port=8000)

        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True
        server_thread.start()

        print("API server started on http://localhost:8000")
        print("Waiting for user login...")

        # Wait for user ID to be set from the frontend
        self.__user_id_set.wait()
        print(f"User logged in: {self.user_id}")

        # Getting and initializing chats
        target_user_ids = await self.__get_chats_from_db()
        for target_user_id in target_user_ids:
            if target_user_id == self.user_id:
                continue
            chat = Chat(
                user_id=self.user_id,
                target_user_id=target_user_id,
                on_message_callback=self.on_message_received)
            self.__chats[target_user_id] = chat
            print(f"Chat loaded: {chat.target_user_id}")
        print(f"All chats loaded: {self.__chats}")

        for chat in self.__chats.values():
            asyncio.create_task(chat.open())

        if self.__chats:
            await asyncio.gather(*[chat.is_opened.wait() for chat in self.__chats.values()])
        print("All chats are opened")

        self.__chats_loaded = True

        while True:
            await asyncio.sleep(1)
