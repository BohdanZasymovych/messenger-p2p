"""module providing classes for messages, requests and class for encryption"""
import os
import json
import uuid
import base64
from datetime import datetime
from nacl.public import PrivateKey, PublicKey, Box
import nacl.secret
import nacl.utils
import nacl.pwhash


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

class SymmetricEncryption:
    """
    Class responsible for encrypting and decrypting
    content the of database using key derived from password
    """
    SALT = b';\xa1\xa0\xcf[\x89\x05\xb6\x06\x8f\x89J\xc8\x8d\x85m'

    def __init__(self):
        self.__password = None
        self.__key = None

    def set_password(self, password: str):
        """Sets the password and derives the key from it"""
        self.__password = password
        self.__key = self.__derive_key_from_password()

    def __derive_key_from_password(self) -> bytes:
        """Derives encryption key from password using Argon2id"""
        key = nacl.pwhash.argon2id.kdf(
            size=nacl.secret.SecretBox.KEY_SIZE,
            password=self.__password.encode('utf-8'),
            salt=self.SALT,
            opslimit=nacl.pwhash.argon2id.OPSLIMIT_INTERACTIVE,
            memlimit=nacl.pwhash.argon2id.MEMLIMIT_INTERACTIVE
        )
        return key

    def encrypt(self, data: str) -> str:
        """Encrypts data using XSalsa20-Poly1305"""
        box = nacl.secret.SecretBox(self.__key)
        encrypted = box.encrypt(data.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypts data using XSalsa20-Poly1305"""
        try:
            box = nacl.secret.SecretBox(self.__key)
            encrypted = base64.b64decode(encrypted_data)
            decrypted = box.decrypt(encrypted)
            return decrypted.decode('utf-8')
        except (nacl.exceptions.CryptoError, ValueError) as e:
            raise ValueError(f"Decryption failed: {e}") from e


class Encryption:
    """Class responsible for encryption of messages"""
    PRIVATE_KEY_PATH = "keys/private_key.key"
    PUBLIC_KEY_PATH = "keys/public_key.key"

    def __init__(self):
        self.__private_key = None
        self.__public_key = None

        self.__peer_public_key = None
        self.box = None

    @property
    def public_key(self) -> str:
        """Returns the public key of the user as string"""
        return base64.b64encode(bytes(self.__public_key)).decode('utf-8')

    def generate_keys(self):
        """Generates and sets the public and private keys"""
        self.__private_key = PrivateKey.generate()
        self.__public_key = self.__private_key.public_key

    @classmethod
    def __generate_long_term_keys(cls, symmetric_encryption: SymmetricEncryption) -> tuple[str, str]:
        """Generates the long term keys and saves them to files"""
        private_key = PrivateKey.generate()
        public_key = private_key.public_key
        private_key_bytes = bytes(private_key)
        public_key_bytes = bytes(public_key)

        encrypted_private_key = symmetric_encryption.encrypt(base64.b64encode(private_key_bytes).decode('utf-8'))
        encrypted_public_key = symmetric_encryption.encrypt(base64.b64encode(public_key_bytes).decode('utf-8'))

        os.makedirs("keys", exist_ok=True)

        with open(cls.PRIVATE_KEY_PATH, "w", encoding="utf-8") as f:
            f.write(encrypted_private_key)

        with open(cls.PUBLIC_KEY_PATH, "w", encoding="utf-8") as f:
            f.write(encrypted_public_key)

        # Convert to base64 strings before returning
        private_key_str = base64.b64encode(private_key_bytes).decode('utf-8')
        public_key_str = base64.b64encode(public_key_bytes).decode('utf-8')

        return private_key_str, public_key_str

    @classmethod
    def load_long_term_keys(cls, symmetric_encryption: SymmetricEncryption) -> tuple[str, str]:
        """Loads or generates keys and returns them as base64 strings"""

        try:
            with open(cls.PRIVATE_KEY_PATH, "r", encoding="utf-8") as f:
                encrypted_private_key = f.read()

            with open(cls.PUBLIC_KEY_PATH, "r", encoding="utf-8") as f:
                encrypted_public_key = f.read()

            # Decrypt the keys
            private_key_str = symmetric_encryption.decrypt(encrypted_private_key)
            public_key_str = symmetric_encryption.decrypt(encrypted_public_key)

        except FileNotFoundError:
            private_key_str, public_key_str = cls.__generate_long_term_keys(symmetric_encryption)

        return private_key_str, public_key_str

    def set_keys(self, private_key: str, public_key: str):
        """Sets the private and public keys of the user"""
        decoded_private_key = base64.b64decode(private_key)
        self.__private_key = PrivateKey(decoded_private_key)

        decoded_public_key = base64.b64decode(public_key)
        self.__public_key = PublicKey(decoded_public_key)

    def set_peer_public_key(self, peer_public_key: str):
        """Sets the public key of the peer"""
        decoded_key = base64.b64decode(peer_public_key)
        self.__peer_public_key = PublicKey(decoded_key)
        self.box = Box(self.__private_key, self.__peer_public_key)

    def encrypt(self, message: str) -> str:
        """Encrypts the message using the box and returns a base64 encoded string"""
        if self.box is None:
            raise ValueError("Peer public key not set")
        encrypted_bytes = self.box.encrypt(message.encode())
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt(self, encrypted_message: str) -> str:
        """Decrypts the base64 encoded encrypted message string"""
        if self.box is None:
            raise ValueError("Peer public key not set")
        encrypted_bytes = base64.b64decode(encrypted_message)
        return self.box.decrypt(encrypted_bytes).decode("utf-8")
