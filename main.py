import asyncio

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.plugins import openai, silero

load_dotenv()

class Assistant(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
            "You are a voice assistant created by LiveKit. Your interface with users will be voice.",
            "You will be a receptionist at a physician office and will facilitate the booking of appointments",
            "You should use short, concise, and natural responses, and avoid usage of unpronouncable punctuation"
            )
        )

async def entrypoint(ctx: JobContext):
    # initial_ctx = llm.ChatContext().append(
    #     role="system",
    #     text=(
    #         "You are a voice assistant created by LiveKit. Your interface with users will be voice.",
    #         "You will be a receptionist at a physician office and will facilitate the booking of appointments",
    #         "You should use short, concise, and natural responses, and avoid usage of unpronouncable punctuation"
    #     )
    # )
    # await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        # chat_ctx=initial_ctx
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        # room_input_options=RoomInputOptions(
        #     # LiveKit Cloud enhanced noise cancellation
        #     # - If self-hosting, omit this parameter
        #     # - For telephony applications, use `BVCTelephony` for best results
        #     noise_cancellation=noise_cancellation.BVC(), 
        # )
    )

    await ctx.connect()
    await asyncio.sleep(1)
    
    await session.say("Hey, how can I help you today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
