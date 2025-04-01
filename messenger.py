import json
import logging
import sys
import asyncio
import websockets
from datetime import datetime
from aioconsole import ainput
from aiortc import (RTCPeerConnection,
                    RTCSessionDescription,
                    RTCDataChannel,
                    RTCConfiguration,
                    RTCIceServer)

LOGGING_FILE = 'logging.log'
logging.basicConfig(level=logging.DEBUG, filename=LOGGING_FILE, filemode='w',
                    format="%(asctime)s - %(levelname)s - %(message)s")

ICE_CONFIG = RTCConfiguration(
    iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
)

SERVER_URL = "ws://localhost:8000"  # URL WebSocket сервера

def set_data_channel_events(data_channel: RTCDataChannel, open_event: asyncio.Event = None):
    """Обробник подій для data channel"""

    data_channel.on('error', lambda error: print("Data channel error:", error))

    @data_channel.on('message')
    def on_message(message):
        print(f'Peer ({datetime.now().strftime("%H:%M:%S")}): {message}')
        logging.debug(f'Message received: {message}')

    @data_channel.on('open')
    def on_open():
        print('Data channel is open')
        if open_event:
            open_event.set()

    @data_channel.on('close')
    def on_close():
        print('\nData channel was closed')
        logging.warning('Exiting program, data channel closed')
        sys.exit(1)

async def message_loop(data_channel: RTCDataChannel):
    """Асинхронний цикл обміну повідомленнями"""
    print()
    while True:
        message = await ainput('You: ')
        if message:
            logging.debug(f'Message sent: {message}')
            data_channel.send(message)

async def run_offer():
    """Функція для `offerer`"""
    data_channel_open_event = asyncio.Event()
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    dc = pc.createDataChannel('channel')
    set_data_channel_events(dc, data_channel_open_event)

    @pc.on("connectionstatechange")
    def on_connection_state_change():
        print(f"Connection state changed: {pc.connectionState}")


    async with websockets.connect(SERVER_URL) as websocket:
        await websocket.send(json.dumps({"type": "register", "user_id": "offerer"}))

        offer = await pc.createOffer()
        logging.info(offer)
        await pc.setLocalDescription(offer)

        await websocket.send(json.dumps({"type": "offer", "sdp": offer.sdp, "user_id": "offerer"}))

        response = await websocket.recv()
        data = json.loads(response)

        if data["type"] == "answer":
            answer = RTCSessionDescription(sdp=data["sdp"], type="answer")
            await pc.setRemoteDescription(answer)

    await data_channel_open_event.wait()
    try:
        await message_loop(dc)
    finally:
        await pc.close()

async def run_answer():
    """Функція для `answerer`"""
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    @pc.on('datachannel')
    def on_datachannel(data_channel):
        logging.info("Data channel received")
        print("Data channel received")
        set_data_channel_events(data_channel)
        asyncio.create_task(message_loop(data_channel))

    @pc.on("connectionstatechange")
    def on_connection_state_change():
        logging.info(f"Connection state changed: {pc.connectionState}")
        print(f"Connection state changed: {pc.connectionState}")

    async with websockets.connect(SERVER_URL) as websocket:
        await websocket.send(json.dumps({"type": "register", "user_id": "answerer"}))
        response = await websocket.recv()
        # print('3')
        data = json.loads(response)
        # print(data)

        if data["type"] == "offer":
            offer = RTCSessionDescription(sdp=data["sdp"], type="offer")
            await pc.setRemoteDescription(offer)
            # print('5')

            answer = await pc.createAnswer()
            # print('6')
            await pc.setLocalDescription(answer)
            # print('7')

            await websocket.send(json.dumps({"type": "answer", "sdp": answer.sdp, "user_id": "answerer"}))
            # print('8')

    try:
        await asyncio.Future()
    finally:
        await pc.close()

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ("offer", "answer"):
        print("Usage: python messenger.py offer|answer")
        logging.warning('Exiting program, incorrect command')
        sys.exit(1)

    role = sys.argv[1]
    if role == "offer":
        asyncio.run(run_offer())
    else:
        asyncio.run(run_answer())
