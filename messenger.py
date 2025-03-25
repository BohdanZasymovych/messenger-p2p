"""messenger.py"""
import json
# import time
from datetime import datetime
import sys
import asyncio
from aioconsole import ainput
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel


# ICE_CONFIG = RTCConfiguration(
#     iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
# )


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
        print('Invalid JSON pasted, try again\n')
    return sdp


def set_data_channel_events(data_channel: RTCDataChannel, open_event: asyncio.Event=None) -> None:
    """Set events behavior for data channel"""

    data_channel.on('error', lambda error: print("Data channel error:", error))
    data_channel.on('message', lambda message: print(f'Peer ({datetime.now().strftime("%H:%M:%S")}): {message}'))

    @data_channel.on('open')
    def on_open():
        print('Data channel is open')
        if open_event:
            open_event.set()

    @data_channel.on('close')
    def on_close():
        print('\nData channel was closed')
        sys.exit(1)

async def message_loop(data_channel: RTCDataChannel) -> None:
    """Asynchronous function which handles receiving messages"""
    print()
    while True:
        message = await ainput('You: ')
        if message:
            data_channel.send(message)


async def run_offer() -> None:
    """Function for user who runs code as offer"""
    data_channel_open_event = asyncio.Event()

    # Create peer connection
    pc = RTCPeerConnection()

    # Create data channel and set its behavior on events
    dc = pc.createDataChannel('channel')
    set_data_channel_events(dc, data_channel_open_event)

    # Set behavior for connection state change
    @pc.on("connectionstatechange")
    def on_connection_state_change():
        print(f"Connection state changed: {pc.connectionState}")

    # Create and set offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

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
    try:
        await message_loop(dc)
    finally:
        await pc.close()


async def run_answer() -> None:
    """Function for user who runs code as answer"""

    # Create peer connection
    pc = RTCPeerConnection()

    # on_datacannel function will be executed when data channel received
    # from user who sent offer
    @pc.on('datachannel')
    def on_datachannel(data_channel):
        """Set behavior when data channel received"""
        print("Data channel received.")
        set_data_channel_events(data_channel)
        if data_channel.readyState == "open":
            print("Data channel is open")

        # Start a task for sending messages from the terminal.
        asyncio.create_task(message_loop(data_channel))

    # Set behavior for connection state change
    @pc.on("connectionstatechange")
    def on_connection_state_change():
        print(f"Connection state changed: {pc.connectionState}")


    # Try to get remote offer from terminal until valid JSON is pasted
    print("Paste remote offer SDP JSON and then press Enter:")
    remote_description_offer = get_sdp()

    # Set offer as remote desciption for peer connection
    await pc.setRemoteDescription(remote_description_offer)

    # Create and set answer as local desciption for peer connection
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

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
        sys.exit(1)

    role = sys.argv[1]
    if role == "offer":
        asyncio.run(run_offer())
    else:
        asyncio.run(run_answer())
