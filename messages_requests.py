"""module providing classes for messages, requests and class for encryption"""
import json
import uuid
from datetime import datetime
from nacl.public import PrivateKey, PublicKey, Box


MESSAGE_NAMESPACE = uuid.UUID("1bc43a13-70f6-49c3-bea7-26f4fcc5b6c8")


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
    def __init__(self, message_type: str, content: str,
                 user_id: str, target_user_id: str, sending_time: Time=Time()):

        self.type = message_type
        self.content = content
        self.sending_time = sending_time
        self.user_id = user_id
        self.target_user_id = target_user_id

    @property
    def json_string(self) -> str:
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
    def unique_id(self) -> str:
        """Returns unique id of the message based on hash"""
        message_info = f"""{self.content}|{self.sending_time.date}
|{self.sending_time.time}|{self.user_id}|{self.target_user_id}"""

        return str(uuid.uuid5(MESSAGE_NAMESPACE, message_info))

    def __str__(self) -> str:
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


class Encryption:
    """Class responsible for encryption of messages"""
    def __init__(self):
        self.__private_key = PrivateKey.generate()
        self.__public_key = self.__private_key.public_key

        self.__peer_public_key = None
        self.box = None

    @property
    def public_key(self) -> PublicKey:
        """Returns the public key of the user"""
        return self.__public_key

    def set_peer_public_key(self, peer_public_key: PublicKey):
        """Sets the public key of the peer"""
        self.__peer_public_key = peer_public_key
        self.box = Box(self.__private_key, self.__peer_public_key)

    def encrypt(self, message: str) -> bytes:
        """Encrypts the message using the box"""
        if self.box is None:
            raise ValueError("Peer public key not set")
        return self.box.encrypt(message.encode())

    def decrypt(self, encrypted_message: bytes) -> str:
        """Decrypts the message using the box"""
        if self.box is None:
            raise ValueError("Peer public key not set")
        return self.box.decrypt(encrypted_message).decode()
