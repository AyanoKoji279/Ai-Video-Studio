import requests
import os
import json

API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def generate_script(topic: str, duration: int) -> dict:
    word_count = duration * 2  # ~2 words per second

    prompt = f"""
    You are a viral content scriptwriter. Write a voiceover script about:
    "{topic}"

    The script must be around {word_count} words, suitable for a {duration}-second video.

    Return your response as a valid JSON object with these keys:
    - "full_text": the complete voiceover script text
    - "scenes": a list of objects, each with:
        - "text": the scene's spoken text
        - "duration": estimated duration in seconds for this scene
        - "search_term": a Pexels search term for stock footage to match this scene
    - "captions": a list of objects, each with:
        - "text": the caption phrase (exactly as it should appear on screen)
        - "start_time": the start time in seconds
        - "end_time": the end time in seconds

    Caption timing must sync with the voiceover. Use dynamic, eye-catching phrases.
    """

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    url = f"{BASE_URL}?key={API_KEY}"

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise Exception(f"Gemini API error: {response.status_code} {response.text}")

    result = response.json()
    raw_text = result["candidates"][0]["content"]["parts"][0]["text"]

    # Parse JSON from the response
    try:
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        data = json.loads(text)
        return data
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "full_text": raw_text,
            "scenes": [
                {"text": raw_text, "duration": duration, "search_term": topic}
            ],
            "captions": [
                {"text": raw_text[:30], "start_time": 0, "end_time": duration}
            ]
        }
