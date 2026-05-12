import streamlit as st
import os
from modules.script_gen import generate_script
from modules.voice_gen import generate_voiceover
from modules.visual_gen import fetch_pexels_videos
from modules.image_gen import generate_ai_image
from modules.video_assembly import assemble_video
import time

st.set_page_config(page_title="AI Video Automation Studio", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Automation Studio")
st.markdown("Create viral YouTube Shorts / TikTok / Reels with AI")

# Sidebar configuration
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
    if os.getenv("GEMINI_API_KEY"):
        st.success("Gemini key set")
    else:
        st.error("Gemini key missing")
    if os.getenv("PEXELS_API_KEY"):
        st.success("Pexels key set")
    else:
        st.error("Pexels key missing")

# Main generation button
if st.button("🎥 Generate Video Now", type="primary"):
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("PEXELS_API_KEY"):
        st.error("Please set GEMINI_API_KEY and PEXELS_API_KEY in environment variables (or Streamlit secrets).")
    else:
        try:
            progress_bar = st.progress(0, text="Starting...")

            # Step 1: Script & captions
            progress_bar.progress(10, text="Generating script & captions...")
            script_data = generate_script(video_topic, duration)

            # Step 2: Voiceover
            progress_bar.progress(30, text="Creating AI voiceover...")
            audio_path = generate_voiceover(script_data["full_text"], voice_speed)

            # Step 3: Visuals
            progress_bar.progress(60, text="Fetching visuals...")
            if use_ai_images:
                image_paths = generate_ai_image(script_data["scenes"])
                video_clips = image_paths
            else:
                video_clips = fetch_pexels_videos(script_data["scenes"])

            # Step 4: Assemble final video
            progress_bar.progress(80, text="Assembling video with music...")
            music_file = f"assets/music/{bg_music}.mp3" if bg_music != "none" else None
            final_path = assemble_video(video_clips, audio_path, script_data["captions"], music_file, caption_style)

            progress_bar.progress(100, text="Done!")
            st.success("✅ Video generated successfully!")

            # Show the video & download
            st.video(final_path)
            with open(final_path, "rb") as f:
                st.download_button("⬇️ Download Video", f, file_name="ai_short.mp4", mime="video/mp4")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e)
            
