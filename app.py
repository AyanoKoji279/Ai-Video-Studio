import streamlit as st
import os
import time
import requests
import json
import asyncio
import tempfile
from moviepy import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, TextClip, ColorClip, CompositeAudioClip
)
from moviepy.video.fx import Resize
import edge_tts
import numpy as np

# ------------------ API KEYS & URLs ------------------
PEXELS_API_KEY = "AgHEaR9dq3fsg71hRFkq8gr8SPHW3HpebnUXsCfKVtvr7GA1SI0azZYf"
PEXELS_URL = "https://api.pexels.com/videos/search"

# ------------------ HELPERS ------------------
OUTPUT_AUDIO = "outputs/audio"
OUTPUT_CLIPS = "outputs/clips"
OUTPUT_IMAGES = "outputs/images"
OUTPUT_FINAL = "outputs/final"
for d in [OUTPUT_AUDIO, OUTPUT_CLIPS, OUTPUT_IMAGES, OUTPUT_FINAL]:
    os.makedirs(d, exist_ok=True)

CAPTION_STYLES = {
    "bold yellow": {"color": "yellow", "stroke_color": "black", "stroke_width": 3, "font_size": 50},
    "clean white": {"color": "white", "stroke_color": "black", "stroke_width": 2, "font_size": 45},
    "neon green": {"color": "#39FF14", "stroke_color": "#0a0a0a", "stroke_width": 4, "font_size": 50},
}
TARGET_SIZE = (1080, 1920)

# ------------------ SCRIPT GENERATION (Free Pollinations API, no key) ------------------
def generate_script(topic: str, duration: int) -> dict:
    word_count = duration * 2  # rough estimate
    prompt = f"""
    You are a viral content scriptwriter. Write a voiceover script about:
    "{topic}"

    The script must be around {word_count} words, suitable for a {duration}-second video.

    Return your response as a valid JSON object with these keys:
    - "full_text": complete voiceover script text
    - "scenes": list of objects, each with "text", "duration", "search_term"
    - "captions": list of objects, each with "text", "start_time", "end_time"

    Only output the JSON object, nothing else.
    """

    response = requests.post(
        "https://text.pollinations.ai/",
        json={"messages": [{"role": "user", "content": prompt}]}
    )

    if response.status_code != 200:
        raise Exception(f"Text generation error: {response.status_code} {response.text}")

    raw_text = response.json().get("content", "")

    # Try to parse JSON from the response
    try:
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text)
    except:
        # Fallback if JSON parsing fails
        return {
            "full_text": raw_text,
            "scenes": [{"text": raw_text, "duration": duration, "search_term": topic}],
            "captions": [{"text": raw_text[:30], "start_time": 0, "end_time": duration}]
        }

# ------------------ VOICEOVER (Edge TTS, free) ------------------
async def _generate_edge(text, filepath, voice="en-US-AriaNeural", rate="+0%"):
    comm = edge_tts.Communicate(text, voice, rate=rate)
    await comm.save(filepath)

def generate_voiceover(text: str, speed: str = "normal", filename: str = "voiceover.mp3") -> str:
    rate_map = {"slow": "-20%", "normal": "+0%", "fast": "+20%"}
    rate = rate_map.get(speed, "+0%")
    output_path = os.path.join(OUTPUT_AUDIO, filename)
    asyncio.run(_generate_edge(text, output_path, rate=rate))
    return output_path

# ------------------ STOCK VIDEOS (Pexels API) ------------------
def fetch_pexels_videos(search_terms, max_clips=5) -> list:
    headers = {"Authorization": PEXELS_API_KEY}
    clips = []
    for term in search_terms:
        if isinstance(term, dict):
            term = term.get("search_term", "")
        if not term:
            continue
        params = {"query": term, "per_page": 1, "size": "medium", "orientation": "portrait"}
        r = requests.get(PEXELS_URL, headers=headers, params=params)
        if r.status_code == 200:
            data = r.json()
            videos = data.get("videos", [])
            if videos:
                video_files = videos[0].get("video_files", [])
                # Prefer portrait HD
                target = next((vf for vf in video_files if vf.get("width")==1080 and vf.get("height")==1920), video_files[0])
                video_url = target["link"]
                ext = video_url.split(".")[-1].split("?")[0]
                fname = f"{term.replace(' ','_')}_{videos[0]['id']}.{ext}"
                fpath = os.path.join(OUTPUT_CLIPS, fname)
                with requests.get(video_url, stream=True) as vresp:
                    vresp.raise_for_status()
                    with open(fpath, "wb") as f:
                        for chunk in vresp.iter_content(8192):
                            f.write(chunk)
                clips.append(fpath)
    return clips

# ------------------ AI IMAGE GENERATOR (Pollinations, free) ------------------
def generate_ai_image(scenes) -> list:
    paths = []
    for i, scene in enumerate(scenes):
        prompt = scene.get("text", "abstract background")
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1080&height=1920&nologo=true"
        try:
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                fpath = os.path.join(OUTPUT_IMAGES, f"scene_{i+1}.jpg")
                with open(fpath, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                paths.append(fpath)
            else:
                paths.append(None)
        except:
            paths.append(None)
    return paths

# ------------------ VIDEO ASSEMBLY ------------------
def assemble_video(visual_paths, audio_path, captions, music_file=None, caption_style="bold yellow"):
    # Prepare visual clips
    visual_clips = []
    for path in visual_paths:
        if path and os.path.exists(path):
            try:
                if path.lower().endswith(('.jpg','.jpeg','.png')):
                    clip = ImageClip(path).set_duration(3)
                else:
                    clip = VideoFileClip(path).without_audio()
                clip = clip.with_effects([Resize(height=TARGET_SIZE[1])])
                if clip.w < TARGET_SIZE[0]:
                    clip = clip.with_effects([Resize(width=TARGET_SIZE[0])])
                clip = clip.set_position("center").crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_SIZE[0], height=TARGET_SIZE[1])
                visual_clips.append(clip)
            except:
                continue
    if not visual_clips:
        visual_clips = [ColorClip(size=TARGET_SIZE, color=(0,0,0), duration=5)]

    voice_audio = AudioFileClip(audio_path)
    video_duration = voice_audio.duration

    # Distribute visual clips to cover duration
    if len(visual_clips) == 1:
        visual_timeline = [visual_clips[0].set_duration(video_duration)]
    else:
        seg_dur = video_duration / len(visual_clips)
        visual_timeline = [clip.set_duration(seg_dur) for clip in visual_clips]

    final_visual = concatenate_videoclips(visual_timeline, method="compose")

    # Add captions
    style = CAPTION_STYLES.get(caption_style, CAPTION_STYLES["bold yellow"])
    caption_clips = []
    for cap in captions:
        txt = cap.get("text", "")
        start = cap.get("start_time", 0)
        end = cap.get("end_time", start + 2)
        if start >= video_duration:
            continue
        if end > video_duration:
            end = video_duration
        if end - start <= 0:
            continue
        txt_clip = (TextClip(txt, font_size=style["font_size"], color=style["color"],
                             stroke_color=style["stroke_color"], stroke_width=style["stroke_width"],
                             font="Arial-Bold", method="caption", size=(TARGET_SIZE[0]*0.9, None))
                    .set_position(("center", "center"))
                    .set_start(start)
                    .set_duration(end - start))
        caption_clips.append(txt_clip)

    composite = CompositeVideoClip([final_visual] + caption_clips, size=TARGET_SIZE)
    composite = composite.set_audio(voice_audio)

    # Mix background music if provided
    if music_file and os.path.exists(music_file):
        music_audio = AudioFileClip(music_file).volumex(0.15)
        if music_audio.duration < video_duration:
            music_audio = music_audio.loop(duration=video_duration)
        else:
            music_audio = music_audio.subclip(0, video_duration)
        final_audio = CompositeAudioClip([voice_audio, music_audio])
        composite = composite.set_audio(final_audio)

    final_path = os.path.join(OUTPUT_FINAL, "final_video.mp4")
    composite.write_videofile(final_path, fps=24, codec="libx264", audio_codec="aac", threads=2, preset="ultrafast")

    # Clean up
    voice_audio.close()
    for c in visual_clips:
        c.close()
    return final_path

# ------------------ STREAMLIT UI ------------------
st.set_page_config(page_title="AI Video Automation Studio", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Automation Studio")
st.markdown("Create viral YouTube Shorts / TikTok / Reels with AI")

with st.sidebar:
    st.header("⚙️ Settings")
    video_topic = st.text_area("Video Topic / Script Idea", "5 mind-blowing facts about space")
    duration = st.slider("Target Duration (seconds)", 15, 60, 30)
    bg_music = st.selectbox("Background Music", ["lofi", "epic", "suspense", "none"], index=3)
    use_ai_images = st.checkbox("Use AI images instead of stock videos", False)
    caption_style = st.selectbox("Caption Style", ["bold yellow", "clean white", "neon green"], index=0)
    voice_speed = st.selectbox("Voiceover Speed", ["normal", "fast", "slow"], index=0)

    st.markdown("---")
    st.markdown("### 🔑 API Status")
    # Only Pexels key is needed now
    if PEXELS_API_KEY:
        st.success("Pexels key set")
    else:
        st.error("Pexels key missing")

if st.button("🎥 Generate Video Now", type="primary"):
    if not PEXELS_API_KEY:
        st.error("Please set PEXELS_API_KEY in environment variables (or Streamlit secrets).")
    else:
        try:
            progress_bar = st.progress(0, text="Starting...")

            progress_bar.progress(10, text="Generating script & captions...")
            script_data = generate_script(video_topic, duration)

            progress_bar.progress(30, text="Creating AI voiceover...")
            audio_path = generate_voiceover(script_data["full_text"], voice_speed)

            progress_bar.progress(60, text="Fetching visuals...")
            if use_ai_images:
                image_paths = generate_ai_image(script_data["scenes"])
                video_clips = image_paths
            else:
                video_clips = fetch_pexels_videos(script_data["scenes"])

            progress_bar.progress(80, text="Assembling video with music...")
            music_file = f"assets/music/{bg_music}.mp3" if bg_music != "none" else None
            final_path = assemble_video(video_clips, audio_path, script_data["captions"], music_file, caption_style)

            progress_bar.progress(100, text="Done!")
            st.success("✅ Video generated successfully!")

            st.video(final_path)
            with open(final_path, "rb") as f:
                st.download_button("⬇️ Download Video", f, file_name="ai_short.mp4", mime="video/mp4")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e)
            
            
