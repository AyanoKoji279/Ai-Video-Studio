import requests
import os
import tempfile

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_URL = "https://api.pexels.com/videos/search"

OUTPUT_DIR = "outputs/clips"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_pexels_videos(search_terms: list, max_clips: int = 5) -> list:
    """
    Fetch stock video clips from Pexels based on search terms.
    Returns a list of local file paths to the downloaded clips.
    """
    headers = {"Authorization": PEXELS_API_KEY}
    clip_paths = []

    for term in search_terms:
        if isinstance(term, dict):
            term = term.get("search_term", "")
        if not term:
            continue

        params = {"query": term, "per_page": 1, "size": "medium", "orientation": "portrait"}
        response = requests.get(PEXELS_URL, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            if videos:
                # Get the lowest-resolution video file for faster processing
                video_files = videos[0].get("video_files", [])
                # Prefer portrait HD, fallback to sd
                target = None
                for vf in video_files:
                    if vf.get("width") == 1080 and vf.get("height") == 1920:
                        target = vf
                        break
                if not target:
                    target = video_files[0] if video_files else None
                if target:
                    video_url = target["link"]
                    file_ext = video_url.split(".")[-1].split("?")[0]
                    filename = f"{term.replace(' ', '_')}_{videos[0]['id']}.{file_ext}"
                    filepath = os.path.join(OUTPUT_DIR, filename)

                    # Download the video clip
                    with requests.get(video_url, stream=True) as r:
                        r.raise_for_status()
                        with open(filepath, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    clip_paths.append(filepath)

    return clip_paths
