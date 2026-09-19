from app.audio.speaker import Speaker


def main():
    speaker = Speaker()

    speaker.speak(
        "Namaste, kya main Ayush ke papa se baat kar raha hoon?"
    )


if __name__ == "__main__":
    main()