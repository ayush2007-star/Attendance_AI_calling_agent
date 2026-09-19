from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_size: str = "small"):
        print("🧠 Loading speech recognition model...")

        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )

        print("✅ Speech recognition model loaded.")

    def transcribe(self, audio_file: str) -> str:

        segments, info = self.model.transcribe(
            audio_file,
            language="hi",
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        )

        return text.strip()