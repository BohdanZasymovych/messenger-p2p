"""Server for handling p2p connection signaling process"""
import asyncio
from objects import Server


SERVER_IP = "0.0.0.0"
SERVER_PORT = 8000


if __name__ == "__main__":
    server = Server(SERVER_IP, SERVER_PORT)
    asyncio.run(server.run())
