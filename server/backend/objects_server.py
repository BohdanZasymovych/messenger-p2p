"""objects related to the server"""
import os
import logging
from datetime import datetime
import asyncio
from typing import Union
import websockets
import asyncpg
from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.server import WebSocketServerProtocol

from request import Request


WebSocket = Union[WebSocketClientProtocol, WebSocketServerProtocol]



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


class IncorrectRequestTypeError(Exception):
    """Exception which is raised when request with incorrect type is received"""


class UserNotRegisteredError(Exception):
    """Exception which is raised when target user is not registered on server"""


class User:
    """Class that represents user on the server side"""
    def __init__(self):
        self.is_online = False # Indicates if user is connected to the server

        # Websocket which is used to comunicate with the server for entire app
        self.main_websocket = None
        # Websockets which are used to comunicate with other users in chats
        self.websockets = {} #  chat with target_user_id: websocket

        self.pending_users = set() # User waiting for you
        self.pended_users = set() # User you are waiting for

        self.long_term_public_key = None
        self.public_keys = {} # Target user id you have chat with: your public key
        self.created_chats = [] # Chats other users created with you

    def disconnect(self):
        """Sets user to default disconnected state"""
        self.is_online = False
        self.pended_users = set()
        self.main_websocket = None
        self.websockets = {}
        self.public_keys = {}


class Server:
    """Class to represent server which handles establishing connection between users"""
    SERVER_DATABASE_URL = os.getenv("DATABASE_URL")

    def __init__(self, ip: str, port: int):
        self.ip: str = ip
        self.port: int = port
        self.__clients: dict[User] = {} # user_id: User

    async def __save_message_to_db(self, user_id: str, target_user_id: str, message: str) -> None:
        """Saves message to the database"""
        conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
        try:
            await conn.execute("""--sql
                INSERT INTO messages (user_id, target_user_id, message)
                VALUES ($1, $2, $3);
            """, user_id, target_user_id, message)
        finally:
            await conn.close()

    async def __get_messages_from_db(self, user_id: str, target_user_id: str) -> list:
        """Gets messages to specified user from the database"""
        conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
        try:
            rows = await conn.fetch("""--sql
                SELECT message FROM messages
                WHERE user_id = $1 AND target_user_id = $2;
            """, target_user_id, user_id)

            await conn.execute("""--sql
                DELETE FROM messages
                WHERE user_id = $1 AND target_user_id = $2;
            """, target_user_id, user_id)

            messages = [row["message"] for row in rows]

            return messages
        finally:
            await conn.close()

    async def __save_key_to_db(self, user_id: str, public_key: str) -> None:
        """Saves public key to the database"""
        print(f"Saving public key for {user_id} to database...")
        conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
        try:
            await conn.execute("""--sql
                INSERT INTO public_keys (user_id, public_key)
                VALUES ($1, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    public_key = EXCLUDED.public_key,
                    timestamp = CURRENT_TIMESTAMP;
            """, user_id, public_key)
        finally:
            await conn.close()
        print(f"Public key for {user_id} saved to database.")

    async def __get_key_from_db(self, user_id: str) -> str:
        """Gets public key from the database"""
        print(f"Getting public key of user: {user_id} from database...")
        conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
        try:
            row = await conn.fetchrow("""--sql
                SELECT public_key FROM public_keys
                WHERE user_id = $1;
            """, user_id)

            if row is None:
                return None

            print(f"Public key of user: {user_id} received from database.")
            return row["public_key"]
        finally:
            await conn.close()

    async def __add_user_to_db(self, user_id: str, email: str, password: str) -> bool:
        """
        Adds user to the database. Assumes password is already hashed via SHA-256 on the client.
        Returns True if user was added, False if user already exists or error occurred.
        """
        print(f"📥 Checking if user {user_id} or email {email} already exists...")

        try:
            conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
            print("🔌 Connected to DB")

            try:
                existing_user = await conn.fetchrow("""
                    SELECT id FROM users WHERE user_id = $1 OR email = $2;
                """, user_id, email)
                print("📊 Existing user check complete.")
            except Exception as e:
                print(f"❌ Error checking for existing user: {e}")
                return False

            if existing_user:
                print("⚠️ User already exists.")
                return False

            try:
                print("💾 Inserting user with client-side hashed password...")

                await conn.execute("""
                    INSERT INTO users (user_id, email, password)
                    VALUES ($1, $2, $3);
                """, user_id, email, password)

                print(f"✅ New user {user_id} inserted into DB.")
                return True

            except Exception as e:
                print(f"❌ Error inserting user into DB: {e}")
                return False

            finally:
                await conn.close()
                print("🔒 DB connection closed.")

        except Exception as conn_err:
            print(f"❌ Failed to connect to DB: {conn_err}")
            return False


    async def __get_user_info_from_db(self, email: str, password: str) -> dict | None:
        """
        Checks user credentials. Password is assumed to be hashed SHA-256 from client.
        """
        conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
        try:
            row = await conn.fetchrow("""
                SELECT user_id, email, password
                FROM users
                WHERE email = $1;
            """, email)

            if row is None:
                return None

            stored_password = row["password"]
            if password == stored_password:
                return {"user_id": row["user_id"], "email": row["email"]}
            else:
                return None
        finally:
            await conn.close()


    def __disconnect_user(self, user_id: str):
        """Disconnect user with given user id"""
        disconnected_user = self.__clients[user_id]

        for pended_user_id in disconnected_user.pended_users:
            self.__clients[pended_user_id].pending_users.discard(user_id)

        self.__clients[user_id].disconnect()
        print(f"User {user_id} was disconnected")

    async def __handle_register_request(self, websocket: WebSocket, user_id: str, data: dict):
        """Function which handles receiving and processing register_request from user"""
        target_user_id = data["target_user_id"]
        client = self.__clients[user_id]
        target_client = self.__clients.setdefault(target_user_id, User())

        public_key = data["public_key"]

        client.websockets[target_user_id] = websocket
        client.is_online = True
        client.public_keys[target_user_id] = public_key

        # Stored messages are sent to the user as one relay_message_request
        stored_messages = await self.__get_messages_from_db(user_id, target_user_id)

        send_stored_messages = Request(
            request_type="send_stored_messages",
            content={"message": stored_messages}
        )
        await websocket.send(send_stored_messages.json_string)

        if target_user_id in target_client.pending_users:
            client.pending_users.discard(target_user_id)
            target_client.pended_users.discard(user_id)

            target_user_public_key = target_client.public_keys[user_id]

            register_response = Request(
                request_type="register_response",
                content={"register_response_type": "connection_establishment_request",
                        "user_id": target_user_id,
                        "role": "answer",
                        "public_key": target_user_public_key}
            )
            await websocket.send(register_response.json_string)
            print(f"Connection establishment request sent: {register_response.json_string}")

            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"user_id": user_id, "role": "offer"}
            )
            await target_client.websockets[user_id].send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent: {connection_establishment_request.json_string}")

        elif target_client.is_online:
            register_response = Request(
                request_type="register_response",
                content = {"register_response_type": "target_user_online"}
                        # "public_key": self.__clients[target_user_id].public_keys[user_id]}
            )
            await websocket.send(register_response.json_string)

        else:
            register_response = Request(
                request_type="register_response",
                content = {"register_response_type": "target_user_offline"}
            )
            await websocket.send(register_response.json_string)

    async def __handle_connection_request(self, websocket: WebSocket, user_id: str, data: dict):
        """Function which handles processing connection_request from user"""
        target_user_id = data["target_user_id"]
        client = self.__clients[user_id]

        if target_user_id not in self.__clients:
            connection_response= Request(
                request_type="connection_response",
                content = {"connection_response_type": "client_not_registered_error"}
            )
            await websocket.send(connection_response.json_string)
            return

        target_client = self.__clients[target_user_id]
        if target_client.is_online:
            connection_establishment_request = Request(
                request_type="connection_establishment_request",
                content={"user_id": user_id,
                        "role": "answer",
                        "public_key": client.public_keys[target_user_id]}
            )

            await target_client.websockets[user_id].send(connection_establishment_request.json_string)
            print(f"Connection establishment request sent to answerer: {connection_establishment_request}")

            connection_response = Request(
                request_type="connection_response",
                content={"connection_response_type": "connection_establishment_request",
                        "role": "offer",
                        "public_key": target_client.public_keys[user_id]}
            )
            await websocket.send(connection_response.json_string)
            print(f"Connection establishment request sent to offerer: {connection_response}")

        else:
            target_client.is_pended = True
            target_client.pending_users.add(user_id)
            client.pended_users.add(target_user_id)

            connection_response = Request(
                request_type="connection_response",
                content = {"connection_response_type": "target_user_offline"}
            )
            await websocket.send(connection_response.json_string)

    async def __handle_share_offer_request(self, user_id: str, data: dict):
        """Sends offer SDP to the target user"""
        target_user_id = data["target_user_id"]
        target_user_websocket = self.__clients[target_user_id].websockets[user_id]
        offer = data["offer"]
        share_offer_request = Request(
            request_type="share_offer_request",
            content={"user_id": target_user_id, "offer": offer}
        )

        await target_user_websocket.send(share_offer_request.json_string)
        print(f"Offer was sent to the target user: {share_offer_request.json_string}")

    async def __handle_share_answer_request(self, user_id: str, data: dict):
        """Sends answer SDP to the target user"""
        target_user_id = data["target_user_id"]
        target_user_websocket = self.__clients[target_user_id].websockets[user_id]
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
        target_client = self.__clients[target_user_id]

        if target_client.is_online:
            target_user_websocket = target_client.websockets[user_id]
            relay_message_request = Request(
                request_type="relay_message_request",
                content={"message": data["message"], "public_key": data["public_key"]}
                )
            await target_user_websocket.send(relay_message_request.json_string)
            print(f"Message from {user_id} to {target_user_id} was relayed.")

        else:
            try:
                await self.__save_message_to_db(
                    user_id=user_id,
                    target_user_id=target_user_id,
                    message=data["message"]
                )
                print(f"Message from {user_id} to {data['target_user']} saved to database.")

            except KeyError as e:
                print(f"Missing key in relay_message_request: {e}")
            except Exception as e:
                print(f"Error while handling relay_message_request: {e}")

    async def __handle_get_target_user_status_request(self, user_id: str, data: dict):
        target_user_id = data["target_user_id"]
        websocket = self.__clients[user_id].websockets[target_user_id]

        target_user_status = self.__clients[target_user_id].is_online
        target_user_public_key = None
        if target_user_status:
            target_user_public_key = self.__clients[target_user_id].public_keys[user_id]

        target_user_status_request = Request(
            request_type="target_user_status_response",
            content={"target_user_status": target_user_status,
                    "public_key": target_user_public_key}
        )
        await websocket.send(target_user_status_request.json_string)
        print(f"Target user status request sent: {target_user_status_request.json_string}")

    async def __handle_send_long_term_public_key_request(self, user_id: str, data: dict):
        """Saves long term public key to the database"""
        public_key = data["long_term_public_key"]
        await self.__save_key_to_db(user_id, public_key)

    async def __handle_get_long_term_public_key_request(self, websocket, data: dict):
        """Gets long term public key from the database"""
        target_user_id = data["target_user_id"]
        public_key = await self.__get_key_from_db(target_user_id)
        if public_key is None:
            raise UserNotRegisteredError("Target user is not registered on the server.")
        get_long_term_public_key_request = Request(
            request_type="get_long_term_public_key_response",
            content={"long_term_public_key": public_key}
        )
        print(f"Long term public key request sent: {get_long_term_public_key_request.json_string}")
        await websocket.send(get_long_term_public_key_request.json_string)

    async def __handle_get_public_key_request(self, user_id: str, data: dict):
        target_user_id = data["target_user_id"]
        public_key = self.__clients[target_user_id].public_key
        if public_key is None:
            raise UserNotRegisteredError("Target user is not registered on the server.")
        get_public_key_request = Request(
            request_type="get_public_key_response",
            content={"public_key": public_key}
        )
        await self.__clients[user_id].websocket.send(get_public_key_request.json_string)

    async def __handle_add_user_to_db_request(self, websocket, data: dict):
        print("🟡 Entered __handle_add_user_to_db_request")

        user_id = data.get("user_id")
        email = data.get("email")
        password = data.get("password")

        print(f"🧾 Received data: username={user_id}, email={email}, password={'*' * len(password) if password else None}")

        if not user_id or not email or not password:
            error_response = Request(
                request_type="add_user_to_data_base_response",
                content={"status": "error", "message": "Missing username, email, or password."}
            )
            await websocket.send(error_response.json_string)
            print("❌ Sent error response: missing fields")
            return

        success = await self.__add_user_to_db(user_id, email, password)

        if success:
            success_response = Request(
                request_type="add_user_to_data_base_response",
                content={"status": "success", "message": "User successfully added."}
            )
        else:
            success_response = Request(
                request_type="add_user_to_data_base_response",
                content={"status": "error", "message": "Username or email already exists."}
            )

        print("📤 Sending response to client:", success_response.json_string)
        await websocket.send(success_response.json_string)


    async def __handle_check_user_exists_request(self, websocket, data: dict):
        """
        Handles login request using email and hashed password from client.
        """
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            error_response = Request(
                request_type="get_user_info_from_data_base_response",
                content={"status": "error", "message": "Missing email or password."}
            )
            await websocket.send(error_response.json_string)
            return

        user_info = await self.__get_user_info_from_db(email, password)
        user_exists = bool(user_info)

        if not user_exists:
            error_response = Request(
                request_type="get_user_info_from_data_base_response",
                content={"status": "error", "message": "Invalid email or password."}
            )
            await websocket.send(error_response.json_string)
            return

        success_response = Request(
            request_type="get_user_info_from_data_base_response",
            content={
                "status": "success",
                "user_exists": True,
                "user_id": user_info["user_id"],
                "password": password  # ⬅️ hashed password from client
            }
        )
        await websocket.send(success_response.json_string)


    async def __handle_user_existance_request(self, websocket, user_id: str, data: dict):
        """Checks if user are registred on the server"""
        target_user_id = data["target_user_id"]
        try:
            conn = await asyncpg.connect(self.SERVER_DATABASE_URL)

            row = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)",
                target_user_id
            )

            user_existance_request = Request(
                request_type="check_user_existance_request",
                content={"target_user_id": target_user_id, "user_existance": bool(row)}
            )
            await websocket.send(user_existance_request.json_string)
        finally:
            await conn.close()


    async def __handle_login_request(self, websocket: WebSocket, user_id: str, data: dict):
        client = self.__clients.setdefault(user_id, User())
        client.main_websocket = websocket
        client.is_online = True

        public_key = data["long_term_public_key"]
        client.long_term_public_key = public_key
        await self.__save_key_to_db(user_id, public_key)

        created_chats_request = Request(
            request_type="created_chats",
            content={"created_chats": client.created_chats}
        )
        await websocket.send(created_chats_request.json_string)
        client.created_chats = []

    async def __handle_create_chat_request(self, user_id: str, data: dict):
        target_user_id = data["target_user_id"]
        target_client = self.__clients[target_user_id]

        if target_client.is_online:
            create_chat_request = Request(
                request_type="create_chat_request",
                content={"target_user_id": user_id}
            )
            await target_client.main_websocket.send(create_chat_request.json_string)

        else:
            target_client.created_chats.append(user_id)

    async def __receive_requests(self, websocket: WebSocket, requests_queue: asyncio.Queue):
        """Function which receives requests from user and adds them to the requests queue"""
        user_id = None
        try:
            async for request in websocket:
                print(f"Request received: {request}")
                request = Request.from_string(request)
                user_id = request.user_id
                requests_queue.put_nowait(request)
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection closed for user: {user_id}")
        except asyncio.CancelledError:
            print("Handler task was cancelled")
            return
        finally:
            if user_id is not None:
                self.__disconnect_user(user_id)

            await websocket.close()

    async def __websocket_handler(self, websocket):
        print("New client connected.")
        requests_queue = asyncio.Queue()
        asyncio.create_task(self.__receive_requests(websocket, requests_queue))

        while True:
            request = await requests_queue.get()
            request_type = request.type
            user_id = request.user_id
            data = request.content

            match request_type:
                case "register_request":
                    await self.__handle_register_request(websocket, user_id, data)
                case "connection_request":
                    await self.__handle_connection_request(websocket, user_id, data)
                case "share_offer_request":
                    await self.__handle_share_offer_request(user_id, data)
                case "share_answer_request":
                    await self.__handle_share_answer_request(user_id, data)
                case "relay_message_request":
                    await self.__handle_relay_message_request(user_id, data)
                case "get_target_user_status_request":
                    await self.__handle_get_target_user_status_request(user_id, data)
                case "send_long_term_public_key_request":
                    await self.__handle_send_long_term_public_key_request(user_id, data)
                case "get_long_term_public_key_request":
                    await self.__handle_get_long_term_public_key_request(websocket, data)
                case "login_request":
                    await self.__handle_login_request(websocket, user_id, data)
                case "create_chat_request":
                    await self.__handle_create_chat_request(user_id, data)
                case "add_user_to_data_base":
                    await self.__handle_add_user_to_db_request(websocket, data)
                case "get_user_info_from_data_base":
                    await self.__handle_check_user_exists_request(websocket, data)
                case "check_user_existance_request":
                    await self.__handle_user_existance_request(websocket, user_id, data)
                case _:
                    raise IncorrectRequestTypeError(f"Incorrect request type in __websocket_handler ({request_type}).")

    async def run(self):
        """Runs websocket server"""
        async with websockets.serve(self.__websocket_handler, self.ip, self.port):
            print("WebSocket server is running")
            await asyncio.Future()
