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

def set_peer_connection_events(peer_connection: RTCPeerConnection):
    """Set events behavior for data channel"""

    @peer_connection.on("connectionstatechange")
    def on_connection_state_change():
        logging.info(f"Connection state changed: {peer_connection.connectionState}")
        print(f"Connection state changed: {peer_connection.connectionState}")

    @peer_connection.on("iceconnectionstatechange")
    def on_ice_state_change():
        logging.info(f"Ice connection state changed: {peer_connection.iceConnectionState}")
        print(f"Ice connection state changed: {peer_connection.iceConnectionState}")

    @peer_connection.on("icegatheringstatechange")
    def on_ice_gathering_change():
        logging.info(f"Ice gathering state changed: {peer_connection.iceGatheringState}")
        print(f"Ice gathering state changed: {peer_connection.iceGatheringState}")

    @peer_connection.on("signalingstatechange")
    def on_signaling_state_change():
        logging.info(f"Signaling state changed: {peer_connection.signalingState}")
        print(f"Signaling state changed: {peer_connection.signalingState}")


def set_data_channel_events(data_channel: RTCDataChannel, open_event: asyncio.Event=None) -> None:
    """Set events behavior for data channel"""

    @data_channel.on("error")
    def on_error(error):
        print("Data channel error:", error)
        logging.error(f"Data channel error: {error}")

    @data_channel.on('message')
    def on_message(message):
        print(f'Peer ({datetime.now().strftime("%H:%M:%S")}): {message}')
        logging.debug(f'Message received: {message}')
        # asyncio.create_task(print_stats(peer_connection))

    @data_channel.on('open')
    def on_open():
        print('Data channel is open')
        if open_event:
            open_event.set()

    @data_channel.on('close')
    def on_close():
        print('\nData channel was closed')
        logging.warning('Exiting program, data channel was closed')
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

    # Create peer connection
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    # Set behavior for connection state change
    set_peer_connection_events(pc)

    # Create data channel and set its behavior on events
    dc = pc.createDataChannel('channel')
    set_data_channel_events(dc, data_channel_open_event)


    # Create and set offer
    offer = await pc.createOffer()
    await asyncio.sleep(5)
    await pc.setLocalDescription(offer)

    logging.info(
        f"Offer created: {dict({'sdp': pc.localDescription.sdp,'type': pc.localDescription.type})}"
    )

    async with websockets.connect(SERVER_URL) as websocket:
        await websocket.send(json.dumps({"type": "register", "user_id": "offerer"}))


        await websocket.send(json.dumps({"type": "offer", "sdp": pc.localDescription.sdp, "user_id": "offerer"}))

        response = await websocket.recv()
        print(f'Response received: {response}')
        data = json.loads(response)

        if data["type"] == "answer":
            answer = RTCSessionDescription(sdp=data["sdp"], type="answer")
            await pc.setRemoteDescription(answer)
            print("remote description set")

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

    @pc.on("iceconnectionstatechange")
    def on_ice_state_change():
        logging.info(f"Ice connection state changed: {pc.iceConnectionState}")
        print(f"Ice connection state changed: {pc.iceConnectionState}")

    @pc.on("icegatheringstatechange")
    def on_ice_gathering_change():
        logging.info(f"Ice gathering state changed: {pc.iceGatheringState}")
        print(f"Ice gathering state changed: {pc.iceGatheringState}")

    @pc.on("signalingstatechange")
    def on_signaling_state_change():
        logging.info(f"Signaling state changed: {pc.signalingState}")
        print(f"Signaling state changed: {pc.signalingState}")

    async with websockets.connect(SERVER_URL) as websocket:
        await websocket.send(json.dumps({"type": "register", "user_id": "answerer"}))
        response = await websocket.recv()
        print(f'Response received: {response}')
        # print('3')
        data = json.loads(response)
        # print(data)

        if data["type"] == "offer":
            offer = RTCSessionDescription(sdp=data["sdp"], type="offer")
            await pc.setRemoteDescription(offer)
            print('remote description set')
            # print('5')

            answer = await pc.createAnswer()
            # print('6')
            await pc.setLocalDescription(answer)
            # print('7')

            await websocket.send(json.dumps({"type": "answer", "sdp": pc.localDescription.sdp, "user_id": "answerer"}))
            print('Answer sent')
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
