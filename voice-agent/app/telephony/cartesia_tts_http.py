import argparse
from pathlib import Path

import httpx

from app.telephony.settings import get_settings


CARTESIA_TTS_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VERSION = "2026-08-14"
REQUEST_BODY = {
    "model_id": "sonic-3.6",
    "transcript": "Hi, thanks for calling Cartesia. How can I help you today?",
    "voice": "47c38ca4-5f35-497b-b1a3-415245fb35e1",
    "output_format": {
        "container": "wav",
        "encoding": "pcm_s16le",
        "sample_rate": 44100,
    },
    "generation_config": {
        "speed": 1,
        "volume": 1,
    },
}


def synthesize_to_file(output_path: Path) -> Path:
    api_key = get_settings().cartesia_api_key
    if not api_key:
        raise RuntimeError(
            "CARTESIA_API_KEY is missing from voice-agent/.env"
        )

    with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
        response = client.post(
            CARTESIA_TTS_URL,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "Cartesia-Version": CARTESIA_VERSION,
            },
            json=REQUEST_BODY,
        )
        response.raise_for_status()

    audio_bytes = response.content
    if not audio_bytes:
        raise RuntimeError("Cartesia returned an empty audio response")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_bytes)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one Cartesia WAV sample with a single HTTP POST."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output.wav"),
        help="Output WAV path (default: output.wav in the current directory).",
    )
    arguments = parser.parse_args()

    saved_path = synthesize_to_file(arguments.output)
    print(f"Saved Cartesia audio to {saved_path.resolve()}")


if __name__ == "__main__":
    main()
