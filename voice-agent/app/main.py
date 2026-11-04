from app.audio.microphone import Microphone
from app.audio.transcriber import Transcriber
from app.audio.speaker import Speaker


def main():
    microphone = Microphone()
    transcriber = Transcriber(model_size="small")
    speaker = Speaker()

    print("\n===== LOCAL VOICE TEST =====")

    input("Press ENTER and speak...")

    audio_file = microphone.record_to_file(
        filename="recordings/input.wav",
        duration=5.0,
    )

    print("\n🧠 Transcribing...")
    text = transcriber.transcribe(audio_file)

    print("\n👤 You said:")
    print(text)

    # Temporary fixed response.
    # Later this will come from the actual AI voice agent.
    response = (
        "Dhanyavaad. Aapki baat note kar li gayi hai."
    )

    print("\n🤖 Agent response:")
    print(response)

    speaker.speak(response)


if __name__ == "__main__":
    main()