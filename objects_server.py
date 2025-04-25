"""objects related to the server"""
import os
import asyncio
from typing import Union
import websockets
import asyncpg
import bcrypt
from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.server import WebSocketServerProtocol

from messages_requests import Request
from exceptions import IncorrectRequestTypeError, UserNotRegisteredError
from loging_setup import setup_logging
setup_logging()

WebSocket = Union[WebSocketClientProtocol, WebSocketServerProtocol]


class User:
    """Class that represents user on the server side"""
    def __init__(self, websocket=None):
        self.is_online = False # Indicates if user is connected to the server
        self.websocket = websocket

        self.role = None

        self.pending_users = set() # User waiting for you
        self.pended_users = set() # User you are waiting for

        self.public_key = None

    def disconnect(self):
        """Sets user to default disconnected state"""
        self.is_online = False
        self.role = None
        self.pended_users = set()
        self.websocket = None
        self.public_key = None


class Server:
    """Class to represent server which handles establishing connection between users"""
    SERVER_DATABASE_URL = os.getenv("DATABASE_URL_SERVER")

    def __init__(self, ip: str, port: int):
        self.ip: str = ip
        self.port: int = port
        self.__clients: dict[User] = {'1': User(), '2': User()} # user_id: User

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
        print(f"Message from {user_id} to {target_user_id} saved to database.")

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

    # async def __add_user_to_db(self, username: str, email: str, password: str) -> None:
    #     """
    #     Adds user to the database with hashed password, if this user is not already in the database.
    #     """
    #     conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
    #     try:
    #         hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    #         await conn.execute("""--sql
    #             INSERT INTO users (username, email, password)
    #             VALUES ($1, $2, $3);
    #         """, username, email, hashed_password)

    #     finally:
    #         await conn.close()

    #     print(f"User {username} with email {email} added to database with hashed password.")

    # async def __add_user_to_db(self, username: str, email: str, password: str) -> bool:
    #     """
    #     Adds user to the database with hashed password, if user with given username or email doesn't exist.
    #     Returns True if user was added, False if already exists.
    #     """
    #     print(f"📥 Checking if user {username} or email {email} already exists...")

    #     conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
    #     try:
    #         existing_user = await conn.fetchrow("""
    #             SELECT id FROM users WHERE username = $1 OR email = $2;
    #         """, username, email)

    #         if existing_user:
    #             print("⚠️ User already exists. Skipping insert.")
    #             return False  # 👈 користувач вже є

    #         hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    #         print(f"🔐 Password hashed: {hashed_password}")

    #         await conn.execute("""
    #             INSERT INTO users (username, email, password)
    #             VALUES ($1, $2, $3);
    #         """, username, email, hashed_password)

    #         print(f"✅ New user {username} inserted into DB.")
    #         return True

    #     except Exception as e:
    #         print(f"❌ Error inserting user into DB: {e}")
    #         return False

    #     finally:
    #         await conn.close()

    async def __add_user_to_db(self, username: str, email: str, password: str) -> bool:
        """
        Adds user to the database with hashed password, if user with given username or email doesn't exist.
        Returns True if user was added, False if already exists or error occurred.
        """
        print(f"📥 Checking if user {username} or email {email} already exists...")

        try:
            conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
            print("🔌 Connected to DB")

            try:
                existing_user = await conn.fetchrow("""
                    SELECT id FROM users WHERE username = $1 OR email = $2;
                """, username, email)
                print("📊 Existing user check complete.")
            except Exception as e:
                print(f"❌ Error checking for existing user: {e}")
                return False

            if existing_user:
                print("⚠️ User already exists.")
                return False

            try:
                print("🔐 Hashing password...")
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                print("💾 Password hashed, inserting user...")

                await conn.execute("""
                    INSERT INTO users (username, email, password)
                    VALUES ($1, $2, $3);
                """, username, email, hashed_password)

                print(f"✅ New user {username} inserted into DB.")
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

    async def __get_user_info_from_db(self, username: str, email: str, password: str) -> list:
        """
        Gets user info by username and email and verifies the password.
        Returns a dictionary with username, email, and password if credentials are valid.
        """
        conn = await asyncpg.connect(self.SERVER_DATABASE_URL)
        try:
            row = await conn.fetchrow("""--sql
                SELECT username, email, password
                FROM users
                WHERE username = $1 AND email = $2;
            """, username, email)

            if row is None:
                return {}

            hashed_password = row["password"]
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                return {
                    "username": row["username"],
                    "email": row["email"],
                    "password": hashed_password  # optionally include or skip
                }

            return {}  # Password doesn't match

        finally:
            await conn.close()

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
        stored_messages = await self.__get_messages_from_db(user_id, target_user_id)
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

    async def __handle_server_connection_request(self, data: dict):
        target_user_id = data["target_user_id"]
        target_user_websocket = self.__clients[target_user_id].websocket
        server_connection_request = Request(
            request_type="server_connection_request",
            content={"target_user_id": target_user_id}
        )
        await target_user_websocket.send(server_connection_request.json_string)
#gfasgfgfds
    async def __handle_get_target_user_status_request(self, user_id: str, data: dict):
        target_user_id = data["target_user_id"]
        websocket = self.__clients[user_id].websocket

        target_user_status_request = Request(
            request_type="target_user_status_response",
            content={"target_user_status": self.__clients[target_user_id].is_online}
        )
        await websocket.send(target_user_status_request.json_string)
        print(f"Target user status request sent: {target_user_status_request.json_string}")

    async def __handle_add_user_to_db_request(self, websocket, data: dict):
        print("🟡 Entered __handle_add_user_to_db_request")  # 👈 Додаємо лог

        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        print(f"🧾 Received data: username={username}, email={email}, password={'*' * len(password) if password else None}")

        if not username or not email or not password:
            error_response = Request(
                request_type="add_user_to_data_base_response",
                content={"status": "error", "message": "Missing username, email, or password."}
            )
            await websocket.send(error_response.json_string)
            print("❌ Sent error response: missing fields")  # 👈
            return

        print("dgfsafsgfwd")
        success = await self.__add_user_to_db(username, email, password)

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
        Handles request to check if user exists in the database by username, email and password.
        Sends back a response with user_exists: True or False.
        """
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if not username or not email or not password:
            error_response = Request(
                request_type="get_user_info_from_data_base_response",
                content={"status": "error", "message": "Missing username, email or password."}
            )
            await websocket.send(error_response.json_string)
            return

        user_info = await self.__get_user_info_from_db(username, email, password)
        user_exists = bool(user_info)

        response = Request(
            request_type="get_user_info_from_data_base",
            content={"status": "success", "user_exists": user_exists}
        )
        await websocket.send(response.json_string)

    async def __handle_key_exchange_request(self, data: dict):
        pass

    async def __receive_requests(self, websocket: WebSocket, requests_queue: asyncio.Queue):
        """Function which receives requests from user and adds them to the requests queue"""
        user_id = None
        try:
            async for request in websocket:
                print(f"Request received: {request}")
                request = Request.from_string(request)
                user_id = request.user_id
                requests_queue.put_nowait(request)
                print("Finish")
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
            print("Request received in __websocket_handler")
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
                case "add_user_to_data_base":
                    await self.__handle_add_user_to_db_request(websocket, data)
                case "get_user_info_from_data_base":
                    await self.__handle_check_user_exists_request(websocket, data)
                case "key_exchange_request":
                    pass
                # case "ping_request":
                #     print("Ping request received")
                #     pong_response = Request(
                #         request_type="ping_request",
                #         content={}
                #     )
                #     await websocket.send(pong_response.json_string)
                case _:
                    raise IncorrectRequestTypeError(f"Incorrect request type in __websocket_handler ({request_type}).")

    async def run(self):
        """Runs websocket server"""
        async with websockets.serve(self.__websocket_handler, self.ip, self.port):
            print(f"WebSocket server is running on ws://{self.ip}:{self.port}")
            await asyncio.Future()