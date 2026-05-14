import streamlit as st
import os
import time
import requests
import json
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip, CompositeAudioClip
)
from moviepy.video.fx import Resize

# ------------------ DIRECTORIES ------------------
OUTPUT_AUDIO = "outputs/audio"
OUTPUT_IMAGES = "outputs/images"
OUTPUT_FINAL = "outputs/final"
for d in [OUTPUT_AUDIO, OUTPUT_IMAGES, OUTPUT_FINAL]:
    os.makedirs(d, exist_ok=True)

CAPTION_STYLES = {
    "bold yellow": {"color": "yellow", "stroke_color": "black", "stroke_width": 3, "font_size": 60},
    "clean white": {"color": "white", "stroke_color": "black", "stroke_width": 2, "font_size": 55},
    "neon green": {"color": "#39FF14", "stroke_color": "#0a0a0a", "stroke_width": 4, "font_size": 60},
}
TARGET_SIZE = (1080, 1920)

# ------------------ FONT LOADING ------------------
FONT_PATH = "DejaVuSans.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = None

def get_font(size):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except:
            pass
    return ImageFont.load_default()

# ------------------ SCRIPT GENERATION (offline fallback + Pollinations) ------------------
def generate_script(topic: str, duration: int) -> dict:
    # OFFLINE FALLBACK (always works, even if no internet)
    fallback = {
        "full_text": (
            f"Welcome to this quick video about {topic}. "
            f"Did you know that {topic} can change the way you see the world? "
            f"Let's explore three mind-blowing facts right now. "
            f"Fact number one: {topic} is more complex than most people realize. "
            f"Fact number two: experts have studied {topic} for decades. "
            f"Fact number three: {topic} will surprise you. "
            f"Stay tuned for more amazing content. Like and subscribe!"
        ),
        "scenes": [
            {"text": f"Welcome to {topic}", "duration": 3, "search_term": topic},
            {"text": f"Fact one about {topic}", "duration": 5, "search_term": topic},
            {"text": f"Fact two about {topic}", "duration": 5, "search_term": topic},
            {"text": f"Fact three about {topic}", "duration": 5, "search_term": "viral"},
        ],
        "captions": [
            {"text": f"{topic}", "start_time": 0, "end_time": 2},
            {"text": "Mind-Blowing Facts", "start_time": 2, "end_time": 5},
            {"text": "Fact #1", "start_time": 5, "end_time": 8},
            {"text": "Fact #2", "start_time": 8, "end_time": 11},
            {"text": "Fact #3", "start_time": 11, "end_time": 14},
            {"text": "Subscribe for more!", "start_time": 14, "end_time": 18},
        ]
    }

    # Try Pollinations API for a better script (optional)
    word_count = max(duration * 3, 40)
    prompt = f"""
    You are a viral content scriptwriter for YouTube Shorts.
    Write a short, punchy voiceover script about: "{topic}".
    Around {word_count} words, suitable for a {duration}-second video.
    Include a hook, facts, and a call-to-action.
    Return ONLY a JSON object: {{"full_text": "...", "scenes": [...], "captions": [...]}}
    Each scene needs "text", "duration", "search_term".
    Each caption needs "text", "start_time", "end_time".
    """
    try:
        resp = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "user", "content": prompt}]},
            timeout=12
        )
        if resp.status_code == 200:
            raw = resp.json().get("content", "")
            if raw.strip():
                raw = raw.strip()
                if raw.startswith("```json"): raw = raw[7:]
                if raw.startswith("```"): raw = raw[3:]
                if raw.endswith("```"): raw = raw[:-3]
                data = json.loads(raw)
                if data.get("full_text"):
                    return data
    except:
        pass

    return fallback

# ------------------ VOICEOVER (gTTS) ------------------
def generate_voiceover(text: str, speed: str = "normal", filename: str = "voiceover.mp3") -> str:
    out = os.path.join(OUTPUT_AUDIO, filename)
    tts = gTTS(text=text, lang="en", slow=(speed == "slow"))
    tts.save(out)
    return out

# ------------------ AI IMAGE GENERATOR (Pollinations) ------------------
def generate_ai_images(scenes) -> list:
    paths = []
    for i, scene in enumerate(scenes):
        prompt = scene.get("text", "abstract background")
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1080&height=1920&nologo=true"
        try:
            r = requests.get(url, stream=True, timeout=20)
            if r.status_code == 200:
                fpath = os.path.join(OUTPUT_IMAGES, f"scene_{i+1}.jpg")
                with open(fpath, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                paths.append(fpath)
            else:
                # Fallback: dark solid color image
                img = Image.new("RGB", TARGET_SIZE, color=(30,30,30))
                fpath = os.path.join(OUTPUT_IMAGES, f"scene_{i+1}_fallback.jpg")
                img.save(fpath)
                paths.append(fpath)
        except:
            img = Image.new("RGB", TARGET_SIZE, color=(30,30,30))
            fpath = os.path.join(OUTPUT_IMAGES, f"scene_{i+1}_fallback.jpg")
            img.save(fpath)
            paths.append(fpath)
    return paths

# ------------------ CAPTION RENDERING (PIL) ------------------
def create_caption_image(text, style):
    font = get_font(style["font_size"])
    dummy = Image.new("RGBA", (1,1), (0,0,0,0))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0,0), text, font=font)
    w = bbox[2] - bbox[0] + 30
    h = bbox[3] - bbox[1] + 30
    img = Image.new("RGBA", (max(w,200), max(h,100)), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    sw = style.get("stroke_width", 2)
    sc = style.get("stroke_color", "black")
    x, y = 15, 15
    # Outline
    for dx in range(-sw, sw+1):
        for dy in range(-sw, sw+1):
            draw.text((x+dx, y+dy), text, font=font, fill=sc)
    # Main text
    draw.text((x, y), text, font=font, fill=style["color"])
    return np.array(img)

# ------------------ VIDEO ASSEMBLY ------------------
def assemble_video(image_paths, audio_path, captions, caption_style="bold yellow"):
    clips = []
    for path in image_paths:
        if path and os.path.exists(path):
            clip = ImageClip(path).with_duration(3)
            clip = clip.with_effects([Resize(height=TARGET_SIZE[1])])
            if clip.w < TARGET_SIZE[0]:
                clip = clip.with_effects([Resize(width=TARGET_SIZE[0])])
            clip = clip.with_position("center").crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_SIZE[0], height=TARGET_SIZE[1])
            clips.append(clip)
    if not clips:
        clips = [ColorClip(size=TARGET_SIZE, color=(30,30,30), duration=5)]

    voice = AudioFileClip(audio_path)
    dur = voice.duration

    if len(clips) == 1:
        vis = [clips[0].with_duration(dur)]
    else:
        seg = dur / len(clips)
        vis = [c.with_duration(seg) for c in clips]

    final_vis = concatenate_videoclips(vis, method="compose")
    style = CAPTION_STYLES.get(caption_style, CAPTION_STYLES["bold yellow"])
    cap_clips = []
    for cap in captions:
        txt = cap.get("text", "")
        start = cap.get("start_time", 0)
        end = cap.get("end_time", start + 2)
        if start >= dur: continue
        if end > dur: end = dur
        if end - start <= 0: continue
        arr = create_caption_image(txt, style)
        cap_clip = (ImageClip(arr)
                    .with_start(start)
                    .with_duration(end - start)
                    .with_position(("center", "center")))
        cap_clips.append(cap_clip)

    comp = CompositeVideoClip([final_vis] + cap_clips, size=TARGET_SIZE)
    comp = comp.with_audio(voice)

    out_path = os.path.join(OUTPUT_FINAL, "final_video.mp4")
    comp.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", threads=2, preset="ultrafast")
    voice.close()
    for c in clips: c.close()
    return out_path

# ------------------ UI ------------------
st.set_page_config(page_title="AI Video Automation Studio", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Automation Studio")
st.markdown("Create viral YouTube Shorts / TikTok / Reels with AI")

with st.sidebar:
    st.header("⚙️ Settings")
    video_topic = st.text_area("Video Topic / Script Idea", "5 mind-blowing facts about space")
    duration = st.slider("Target Duration (seconds)", 15, 60, 30)
    caption_style = st.selectbox("Caption Style", ["bold yellow", "clean white", "neon green"], index=0)
    voice_speed = st.selectbox("Voiceover Speed", ["normal", "slow"], index=0)
    st.markdown("---")
    st.success("Using free AI images (no API keys needed)")

if st.button("🎥 Generate Video Now", type="primary"):
    try:
        progress = st.progress(0, text="Starting...")

        progress.progress(10, text="Generating script...")
        script = generate_script(video_topic, duration)

        # Show script in an expander (optional, for debugging)
        with st.expander("🔍 See generated script"):
            st.json(script)

        progress.progress(30, text="Creating voiceover...")
        audio = generate_voiceover(script["full_text"], voice_speed)

        progress.progress(60, text="Generating AI images...")
        images = generate_ai_images(script["scenes"])

        progress.progress(80, text="Assembling video...")
        final = assemble_video(images, audio, script["captions"], caption_style)

        progress.progress(100, text="Done!")
        st.success("✅ Video generated!")
        st.video(final)
        with open(final, "rb") as f:
            st.download_button("⬇️ Download Video", f, file_name="ai_short.mp4", mime="video/mp4")
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.exception(e)
