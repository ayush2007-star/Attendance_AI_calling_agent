from agents.realtime import RealtimeAgent, RealtimeRunner


def create_voice_agent() -> RealtimeAgent:
    return RealtimeAgent(
        name="Attendance Voice Agent",
        instructions="""
You are an attendance communication assistant for a college.

Speak naturally, politely, and briefly.

For this development test:
- Greet the parent politely.
- Explain that you are calling from the college.
- Ask whether you are speaking with the student's parent/guardian.
- Ask how you can help.
- Wait for the parent's response.
- Do not invent student information.
- Keep the conversation conversational.
""",
    )


def create_runner() -> RealtimeRunner:
    agent = create_voice_agent()

    return RealtimeRunner(
        starting_agent=agent,
        config={
            "model_settings": {
                "model_name": "gpt-realtime-2.1",
                "audio": {
                    "input": {
                        "format": "pcm16",
                        "transcription": {
                            "model": "gpt-4o-mini-transcribe",
                        },
                        "turn_detection": {
                            "type": "semantic_vad",
                            "interrupt_response": True,
                        },
                    },
                    "output": {
                        "format": "pcm16",
                        "voice": "ash",
                    },
                },
            }
        },
    )