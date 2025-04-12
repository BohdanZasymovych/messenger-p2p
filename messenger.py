"""p2p messenger with signaling process via server"""

import asyncio
from objects import Chat


async def main():
    """Launches chat"""
    chat = Chat()
    await chat.open()

if __name__ == "__main__":
    asyncio.run(main())
