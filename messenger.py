"""p2p messenger with signaling process via server"""
import asyncio
from aioconsole import ainput
from datetime import datetime

from objects import Message, Connection


def get_user_input():
    user_id = input("Enter your user ID: ").strip()
    target_user_id = input("Enter the ID of the user you want to connect to: ").strip()
    return user_id, target_user_id


async def main():
    try:
        user_id, target_user_id = get_user_input()
        message_queue = asyncio.Queue()
        connection = Connection(user_id, target_user_id)
        # await connection.connect_to_server()


        async def on_disconnect(connection: Connection):
            await connection.data_channel_closing_event.wait()
            await connection.p2p_disconnect()


        async def message_loop():
            """Asynchronous function which handles receiving messages"""
            print()
            while True:
                message = await ainput('You: ')
                if message:
                    message_queue.put_nowait(Message(
                                                message_type="message",
                                                content=message,
                                                sending_time=datetime.now().strftime('%H:%M:%S')))


        async def send_message(message: Message, connection: Connection):
            if connection.p2p_connection_state == "connected":
                connection.data_channel.send(message.json_string)
            else:
                is_connected = await connection.connect()
                if is_connected:
                    connection.data_channel.send(message.json_string)
                else:
                    raise Exception("Connection failed")


        async def send_message_loop(connection):
            while True:
                message = await message_queue.get()
                await send_message(message, connection)


        disconnect_task = asyncio.create_task(on_disconnect(connection))
        message_task = asyncio.create_task(message_loop())
        send_task = asyncio.create_task(send_message_loop(connection))

        await asyncio.gather(disconnect_task, message_task, send_task)

    finally:
        await connection.websocket.close()
        await connection.p2p_disconnect()


if __name__ == "__main__":
    asyncio.run(main())
