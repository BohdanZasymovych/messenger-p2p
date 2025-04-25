"""Custom exceptions"""


class IncorrectRequestTypeError(Exception):
    """Exception which is raised when request with incorrect type is received"""


class ConnectionTimeoutError(Exception):
    """Exception which is raised when connection is not established within certain amount of time"""


class UserNotRegisteredError(Exception):
    """Exception which is raised when target user is not registered on server"""
