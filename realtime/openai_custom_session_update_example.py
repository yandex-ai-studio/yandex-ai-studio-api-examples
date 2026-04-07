"""
Yandex Realtime API — Example with Custom Session Update
==================================================================

This example demonstrates how to connect to the Yandex Realtime API
using the OpenAI Python SDK, send a custom ``session.update`` event to configure
speech recognition and synthesis settings, and run a full-duplex voice conversation
(microphone → API → speaker).

Prerequisites
-------------
Install the required dependencies::

    pip install openai sounddevice numpy httpx

Environment variables
---------------------
Set the following variables before running the script:

    YANDEX_IAM_TOKEN    Your Yandex Cloud IAM token (required).
                        Obtain one with the Yandex Cloud CLI::

                            yc iam create-token

                        Or via the REST API:
                        https://yandex.cloud/docs/iam/operations/iam-token/create

    YANDEX_FOLDER_ID    Your Yandex Cloud folder ID (required).
                        Found in the Yandex Cloud console URL or folder settings.

Usage
-----
    export YANDEX_IAM_TOKEN="$(yc iam create-token)"
    export YANDEX_FOLDER_ID="your-folder-id"
    python openai_custom_session_update_example.py

Press Ctrl+C to stop the session.
"""

import asyncio
import base64
import json
import os
import sys

import httpx
import numpy as np
import sounddevice as sd
from openai import AsyncOpenAI
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnectionManager

_IAM_TOKEN = os.environ.get("YANDEX_IAM_TOKEN", "")
_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID", "")

WSS_BASE = os.environ.get(
    "YANDEX_WSS_BASE",
    "wss://ai.api.cloud.yandex.net/v1",
)
REST_BASE = os.environ.get(
    "YANDEX_REST_BASE",
    "https://ai.api.cloud.yandex.net/v1",
)

# Model URI is derived from your folder ID.
# You may override it entirely via the YANDEX_MODEL env var.
MODEL = os.environ.get(
    "YANDEX_MODEL",
    f"gpt://{_FOLDER_ID}/speech-realtime-250923" if _FOLDER_ID else "",
)


SAMPLE_RATE = 44100    # Hz — must match the session.update audio format below
CHANNELS = 1           # Mono
CHUNK_DURATION_S = 0.1 # seconds per microphone chunk
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_DURATION_S)


async def mic_sender(connection, stop_event: asyncio.Event) -> None:
    """Capture audio from the default microphone and stream it to the API.

    Audio is converted from float32 to int16 PCM and sent as
    ``input_audio_buffer.append`` events.
    """
    loop = asyncio.get_event_loop()
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()

    def _callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            print(f"[mic] status: {status}")
        pcm16 = (indata[:, 0] * 32767.0).astype(np.int16)
        loop.call_soon_threadsafe(audio_queue.put_nowait, pcm16.tobytes())

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=CHUNK_FRAMES,
        callback=_callback,
    ):
        print("[mic] Microphone open — streaming at 44 100 Hz. Press Ctrl+C to stop.")
        while not stop_event.is_set():
            try:
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            b64 = base64.b64encode(chunk).decode("utf-8")
            await connection.send(
                {"type": "input_audio_buffer.append", "audio": b64}
            )  # type: ignore[arg-type]


async def audio_player(
    stop_event: asyncio.Event,
    playback_queue: asyncio.Queue,
) -> None:
    """Read PCM16 audio chunks from the queue and play them through the speaker."""
    stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )
    stream.start()
    try:
        while not stop_event.is_set():
            try:
                chunk: bytes = await asyncio.wait_for(playback_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            stream.write(np.frombuffer(chunk, dtype=np.int16))
    finally:
        stream.stop()
        stream.close()
        print("[player] Audio stream closed.")


async def event_receiver(
    connection,
    stop_event: asyncio.Event,
    playback_queue: asyncio.Queue,
) -> None:
    """Listen for events from the API and dispatch them accordingly.

    Audio delta events are forwarded to the playback queue; all other
    events are logged to stdout.
    """
    async for event in connection:
        etype = event.type

        if etype == "session.updated":
            print("\n[event] session.updated:", event.session)

        elif etype == "input_audio_buffer.speech_started":
            print("[event] speech_started — VAD detected voice")

        elif etype == "input_audio_buffer.speech_stopped":
            print("[event] speech_stopped — VAD end of utterance")

        elif etype == "input_audio_buffer.committed":
            print("[event] buffer committed")

        elif etype == "conversation.item.created":
            print("[event] conversation.item.created")

        elif etype == "response.created":
            print("[event] response.created")

        elif etype == "response.output_audio.delta":
            audio_bytes = base64.b64decode(event.delta)
            await playback_queue.put(audio_bytes)

        elif etype == "response.output_audio.done":
            print("[event] response.audio.done")

        elif etype == "response.done":
            print("[event] response.done:", event)

        elif etype == "error":
            print("[event] Error:", event.error)
            stop_event.set()
            break

        else:
            print(f"[event] {etype}")

        if stop_event.is_set():
            break


async def main() -> None:
    # Validate required configuration
    missing = [name for name, val in (
        ("YANDEX_IAM_TOKEN", _IAM_TOKEN),
        ("YANDEX_FOLDER_ID", _FOLDER_ID),
    ) if not val]
    if missing:
        print(
            "[error] The following required environment variables are not set: "
            + ", ".join(missing)
        )
        print("        See the module docstring for setup instructions.")
        sys.exit(1)

    print(f"[config] WSS base  : {WSS_BASE}")
    print(f"[config] Model     : {MODEL}")

    client = AsyncOpenAI(
        api_key=_IAM_TOKEN,
        base_url=REST_BASE,
        websocket_base_url=WSS_BASE
    )

    async with client.realtime.connect(
        model=MODEL,
        websocket_connection_options={"max_size": None},
    ) as connection:

        custom_session_update = {
            "type": "session.update",
            "session": {
                "tools": [
                    {
                        "type": "function",
                        "name": "web_search", # Use web-search tool
                    }
                ],
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": SAMPLE_RATE,
                        },
                        # Languages the STT engine will recognise.
                        # Full list: https://aistudio.yandex.ru/docs/ru/speechkit/stt/models.html
                        "languages": ["ru-RU"],
                    },
                    "output": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": SAMPLE_RATE,
                        },
                        "voice": "alena",
                        # Voice role (emotion). Available roles per voice:
                        # https://aistudio.yandex.ru/docs/ru/speechkit/tts/voices.html
                        "role": "good",
                    },
                },
            },
        }

        await connection.send(custom_session_update)  # type: ignore[arg-type]
        print("\n[session] session.update sent:")
        print(json.dumps(custom_session_update, indent=2, ensure_ascii=False))

        stop_event = asyncio.Event()
        playback_queue: asyncio.Queue[bytes] = asyncio.Queue()

        tasks = [
            asyncio.create_task(mic_sender(connection, stop_event)),
            asyncio.create_task(event_receiver(connection, stop_event, playback_queue)),
            asyncio.create_task(audio_player(stop_event, playback_queue)),
        ]

        try:
            await asyncio.gather(*tasks)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n[main] Stopping…")
        finally:
            stop_event.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
