"""p2p messenger with signaling process via server"""
import asyncio
from objects_user import Chat


async def main():
    """Launches chat"""
    user_id = input("Enter your user ID: ")
    target_user_id = input("Enter target user ID: ")
    chat = Chat(user_id, target_user_id)
    await chat.open()

if __name__ == "__main__":
    asyncio.run(main())
