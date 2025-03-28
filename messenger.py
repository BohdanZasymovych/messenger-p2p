"""messenger.py"""
import json
import logging
from datetime import datetime
import sys
import asyncio
from aioconsole import ainput
from aiortc import (RTCPeerConnection,
                    RTCSessionDescription,
                    RTCDataChannel,
                    RTCConfiguration,
                    RTCIceServer)


LOGGING_FILE = 'logging.log'
logging.basicConfig(level=logging.DEBUG, filename=LOGGING_FILE, filemode='w',
                    format="%(asctime)s - %(levelname)s - %(message)s")


# Configure ICE with a STUN server.
ICE_CONFIG = RTCConfiguration(
    iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
)


def read_sdp() -> RTCSessionDescription | None:
    """
    Reads SDP from terminal

    return: RTCSessionDescription object if JSON is valid else None
    """
    lines = []
    line = sys.stdin.readline().strip()

    while line:
        lines.append(line)
        line = sys.stdin.readline().strip()

    lines = ''.join(lines)

    try:
        sdp_json = json.loads(lines)
    except json.JSONDecodeError:
        return None

    logging.info(f'SDP json received: {sdp_json}')

    return RTCSessionDescription(sdp=sdp_json["sdp"], type=sdp_json["type"])


def get_sdp() -> RTCSessionDescription:
    """
    Reads SDP JSONs from terminal until valid one is pasted

    return: RTCSessionDescription object
    """
    while True:
        sdp = read_sdp()
        if sdp is not None:
            break
        print('Invalid JSON pasted, try again:')
    return sdp


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


async def message_loop(data_channel: RTCDataChannel) -> None:
    """Asynchronous function which handles receiving messages"""
    print()
    while True:
        message = await ainput('You: ')
        if message:
            data_channel.send(message)
            logging.debug(f'Message sended: {message}')


async def run_offer() -> None:
    """Function for user who runs code as offer"""
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
    await pc.setLocalDescription(offer)

    logging.info(
        f"Offer created: {dict({'sdp': pc.localDescription.sdp,'type': pc.localDescription.type})}"
    )

    # Print offer JSON for user to copy and share with peer
    print("\n=== Copy the following offer SDP and send it to your peer ===\n")
    print(
        json.dumps({
            'sdp': pc.localDescription.sdp,
            'type': pc.localDescription.type
        })
    )
    print()

    # Try to get answer JSON from terminal until valid JSON is pasted
    print("Paste remote answer SDP JSON and then press Enter:")
    remote_description = get_sdp()

    # Set answer as remote description for peer connection
    await pc.setRemoteDescription(remote_description)

    # Wait untill data channel is open
    await data_channel_open_event.wait()

    # Start infinite message loop (while connection is not closed)
    asyncio.create_task(message_loop(dc))
    try:
        await asyncio.Future()
    finally:
        await pc.close()


async def run_answer() -> None:
    """Function for user who runs code as answer"""

    # Create peer connection
    pc = RTCPeerConnection(configuration=ICE_CONFIG)

    # Set behavior for connection state change
    set_peer_connection_events(pc)

    # on_datacannel function will be executed when data channel received
    # from user who sent offer
    @pc.on('datachannel')
    def on_datachannel(data_channel):
        """Set behavior when data channel received"""
        logging.info("Data channel received")
        print("Data channel received")
        set_data_channel_events(data_channel)

        # Start a task for sending messages from the terminal.
        asyncio.create_task(message_loop(data_channel))


    # Try to get remote offer from terminal until valid JSON is pasted
    print("Paste remote offer SDP JSON and then press Enter:")
    remote_description_offer = get_sdp()

    # Set offer as remote desciption for peer connection
    await pc.setRemoteDescription(remote_description_offer)

    # Create answer and set it as local desciption for peer connection
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    logging.info(
        f"Answer created: {dict({'sdp': pc.localDescription.sdp,'type': pc.localDescription.type})}"
    )

    # Print answer JSON for user to copy and share with peer
    print("\n=== Copy the following answer SDP and send it to your peer ===\n")
    print(
        json.dumps({
            'sdp': pc.localDescription.sdp,
            'type': pc.localDescription.type
        })
    )
    print()

    # Wait indefinitely (or until the connection is closed)
    try:
        await asyncio.Future()
    finally:
        await pc.close()


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ("offer", "answer"):
        print("Usage: python p2p_chat.py offer|answer")
        logging.warning('Exiting program, incorrect command')
        sys.exit(1)

    role = sys.argv[1]
    if role == "offer":
        asyncio.run(run_offer())
    else:
        asyncio.run(run_answer())
