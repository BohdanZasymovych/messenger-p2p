"""p2p messenger with signaling process via server"""
import asyncio
from objects_user import App


async def main():
    """Main function to run the messenger app."""
    app = App()
    try:
        await app.open()
    finally:
        await app.close()

if __name__ == "__main__":
    asyncio.run(main())
