"""p2p messenger with signaling process via server"""
import json
from datetime import datetime
import logging
import sys
import asyncio
import websockets
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

SERVER_URL = "ws://0.0.0.0:8000"  # URL of websocket server with ip, port
# SERVER_URL = "ws://10.10.227.118:8000"


def set_peer_connection_events(peer_connection: RTCPeerConnection):
    """Set events behavior for data channel"""
    @peer_connection.on("connectionstatechange")
    def on_connection_state_change():
        logging.info("Connection state changed: %s", peer_connection.connectionState)
        print("Connection state changed: %s", peer_connection.connectionState)

    @peer_connection.on("iceconnectionstatechange")
    def on_ice_state_change():
        logging.info("Ice connection state changed: %s", peer_connection.iceConnectionState)
        print("Ice connection state changed: %s", peer_connection.iceConnectionState)

    @peer_connection.on("icegatheringstatechange")
    def on_ice_gathering_change():
        logging.info("Ice gathering state changed: %s", peer_connection.iceGatheringState)
        print("Ice gathering state changed: %s", peer_connection.iceGatheringState)

    @peer_connection.on("signalingstatechange")
    def on_signaling_state_change():
        logging.info("Signaling state changed: %s", peer_connection.signalingState)
        print("Signaling state changed: %s", peer_connection.signalingState)


def set_data_channel_events(data_channel: RTCDataChannel, open_event: asyncio.Event=None) -> None:
    """Set events behavior for data channel"""
    @data_channel.on("error")
    def on_error(error):
        print("Data channel error:", error)
        logging.error("Data channel error: %s", error)

    @data_channel.on('message')
    def on_message(message):
        print(f"Peer ({datetime.now().strftime('%H:%M:%S')}): {message}")
        logging.debug("Message received: %s", message)

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
    """Asynchronous function which handles receiving messages"""
    print()
    while True:
        message = await ainput('You: ')
        if message:
            logging.debug("Message sent: %s", message)
            data_channel.send(message)


async def run_offer():
    """Function for user who runs code as offerer"""
    data_channel_opening_event = asyncio.Event()

    # Create peer connection
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    # Set behavior for connection state change
    set_peer_connection_events(pc)

    # Create data channel and set its behavior on events
    dc = pc.createDataChannel('channel')
    set_data_channel_events(dc, data_channel_opening_event)

    # Create and set offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    logging.info(
        "Offer created: %s", {'sdp': pc.localDescription.sdp,'type': pc.localDescription.type}
    )

    async with websockets.connect(SERVER_URL) as websocket:
        await websocket.send(json.dumps({"type": "register", "user_id": "offerer"}))
        await websocket.send(json.dumps({"type": "offer", "sdp": pc.localDescription.sdp, "user_id": "offerer"}))

        response = await websocket.recv()
        # print(f'Response received: {response}')
        data = json.loads(response)

        if data["type"] == "answer":
            answer = RTCSessionDescription(sdp=data["sdp"], type="answer")
            await pc.setRemoteDescription(answer)
            print("remote description set")

    await data_channel_opening_event.wait()
    try:
        await message_loop(dc)
    finally:
        await pc.close()


async def run_answer():
    """Function for user who runs code as answer"""
    pc = RTCPeerConnection(configuration=ICE_CONFIG)
    set_peer_connection_events(pc)

    @pc.on('datachannel')
    def on_datachannel(data_channel):
        logging.info("Data channel received")
        print("Data channel received")
        set_data_channel_events(data_channel)
        asyncio.create_task(message_loop(data_channel))

    async with websockets.connect(SERVER_URL) as websocket:
        await websocket.send(json.dumps({"type": "register", "user_id": "answerer"}))

        response = await websocket.recv()
        # print(f'Response received: {response}')
        data = json.loads(response)

        if data["type"] == "offer":
            offer = RTCSessionDescription(sdp=data["sdp"], type="offer")
            await pc.setRemoteDescription(offer)

            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            await websocket.send(json.dumps({"type": "answer", "sdp": pc.localDescription.sdp, "user_id": "answerer"}))

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
