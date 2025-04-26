"""p2p messenger with signaling process via server"""
import asyncio
from objects_user import App


# async def main():
#     """Launches chat"""
#     user_id = input("Enter your user ID: ")
#     target_user_id = input("Enter target user ID: ")
#     chat = Chat(user_id, target_user_id)
#     await chat.open()

async def main():
    app = App()
    await app.open()

if __name__ == "__main__":
    asyncio.run(main())
