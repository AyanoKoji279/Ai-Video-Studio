import edge_tts
import asyncio
import os

OUTPUT_DIR = "outputs/audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def _generate_edge_tts(text: str, output_path: str, voice: str = "en-US-AriaNeural", rate: str = "+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def generate_voiceover(text: str, speed: str = "normal", output_filename: str = "voiceover.mp3") -> str:
    """
    Generate voiceover using Edge TTS (free, high quality).
    Returns the path to the generated audio file.
    """
    # Map speed to rate string
    rate_map = {
        "slow": "-20%",
        "normal": "+0%",
        "fast": "+20%"
    }
    rate = rate_map.get(speed, "+0%")

    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Run async function
    asyncio.run(_generate_edge_tts(text, output_path, rate=rate))

    return output_path
