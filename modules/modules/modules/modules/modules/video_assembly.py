import os
import tempfile
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, TextClip, ColorClip
)
from moviepy.video.fx import resize, crop
import numpy as np

OUTPUT_DIR = "outputs/final"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Caption style presets
CAPTION_STYLES = {
    "bold yellow": {"color": "yellow", "stroke_color": "black", "stroke_width": 3, "font_size": 50},
    "clean white": {"color": "white", "stroke_color": "black", "stroke_width": 2, "font_size": 45},
    "neon green": {"color": "#39FF14", "stroke_color": "#0a0a0a", "stroke_width": 4, "font_size": 50},
}

TARGET_SIZE = (1080, 1920)  # vertical 9:16

def assemble_video(visual_paths: list, audio_path: str, captions: list, music_file: str = None, caption_style: str = "bold yellow") -> str:
    """
    Assemble the final video from clips/images, voiceover, and optional background music.
    Returns path to the final MP4.
    """
    if not visual_paths:
        # Create a blank black clip as fallback
        blank = ColorClip(size=TARGET_SIZE, color=(0,0,0), duration=5)
        visual_clips = [blank]
    else:
        visual_clips = []
        for path in visual_paths:
            if path and os.path.exists(path):
                try:
                    if path.lower().endswith(('.jpg', '.jpeg', '.png')):
                        clip = ImageClip(path).set_duration(3)  # default 3s per image
                    else:
                        clip = VideoFileClip(path).without_audio()
                    # Resize to fit target dimensions
                    clip = clip.resize(height=TARGET_SIZE[1])
                    if clip.w < TARGET_SIZE[0]:
                        clip = clip.resize(width=TARGET_SIZE[0])
                    clip = clip.set_position("center").crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_SIZE[0], height=TARGET_SIZE[1])
                    visual_clips.append(clip)
                except Exception:
                    continue
        if not visual_clips:
            blank = ColorClip(size=TARGET_SIZE, color=(0,0,0), duration=5)
            visual_clips = [blank]

    # Load voiceover audio
    if not audio_path or not os.path.exists(audio_path):
        raise FileNotFoundError("Voiceover audio not found.")

    voice_audio = AudioFileClip(audio_path)
    video_duration = voice_audio.duration

    # Distribute visual clips to cover the audio duration
    if len(visual_clips) == 1:
        visual_timeline = [visual_clips[0].set_duration(video_duration)]
    else:
        segment_duration = video_duration / len(visual_clips)
        visual_timeline = [clip.set_duration(segment_duration) for clip in visual_clips]

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

        duration = end - start
        if duration <= 0:
            continue

        txt_clip = (TextClip(txt, font_size=style["font_size"], color=style["color"],
                             stroke_color=style["stroke_color"], stroke_width=style["stroke_width"],
                             font="Arial-Bold", method="caption", size=(TARGET_SIZE[0]*0.9, None))
                    .set_position(("center", "center"))
                    .set_start(start)
                    .set_duration(duration))
        caption_clips.append(txt_clip)

    composite = CompositeVideoClip([final_visual] + caption_clips, size=TARGET_SIZE)
    composite = composite.set_audio(voice_audio)

    # Mix in background music if provided (lower volume)
    if music_file and os.path.exists(music_file):
        music_audio = AudioFileClip(music_file).volumex(0.15)  # quiet background
        # Loop music if shorter than video
        if music_audio.duration < video_duration:
            music_audio = music_audio.loop(duration=video_duration)
        else:
            music_audio = music_audio.subclip(0, video_duration)
        final_audio = CompositeVideoClip([composite]).audio  # get the current audio
        mixed_audio = CompositeAudioClip([final_audio, music_audio])
        composite = composite.set_audio(mixed_audio)

    # Write final video
    output_path = os.path.join(OUTPUT_DIR, "final_video.mp4")
    composite.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=2, preset="ultrafast")

    # Cleanup
    voice_audio.close()
    for clip in visual_clips:
        clip.close()

    return output_path
