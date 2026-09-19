import sounddevice as sd
import soundfile as sf


class Microphone:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels

    def record_to_file(
        self,
        filename: str = "recordings/input.wav",
        duration: float = 5.0,
    ) -> str:

        print("🎤 Speak now...")

        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )

        sd.wait()

        sf.write(
            filename,
            audio,
            self.sample_rate,
        )

        print(f"✅ Audio saved: {filename}")

        return filename