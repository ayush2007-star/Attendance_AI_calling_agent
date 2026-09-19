import pyttsx3


class Speaker:
    def __init__(self):
        self.engine = pyttsx3.init()

        self.engine.setProperty("rate", 160)
        self.engine.setProperty("volume", 1.0)

    def speak(self, text: str) -> None:
        print(f"🤖 Agent: {text}")

        self.engine.say(text)
        self.engine.runAndWait()