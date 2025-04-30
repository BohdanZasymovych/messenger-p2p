"""module providing classes for messages, requests and class for encryption"""
import json


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
