import os
import base64
import aiohttp
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO = os.getenv("GITHUB_REPO")
TRANSCRIPT_BASE_URL = os.getenv("TRANSCRIPT_BASE_URL", "").rstrip("/")

async def upload_file_to_github(path_in_repo: str, content: str, commit_message: str = "Add transcript") -> str:
    if not all([GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO, TRANSCRIPT_BASE_URL]):
        raise RuntimeError("Missing GitHub environment variables.")

    api_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{path_in_repo}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    async with aiohttp.ClientSession(headers=headers) as session:
        sha = None

        async with session.get(api_url) as resp:
            if resp.status == 200:
                existing = await resp.json()
                sha = existing.get("sha")
            elif resp.status != 404:
                error_text = await resp.text()
                raise RuntimeError(f"GitHub lookup failed: {resp.status} - {error_text}")

        payload = {
            "message": commit_message,
            "content": encoded_content,
            "branch": "main",
        }

        if sha:
            payload["sha"] = sha

        async with session.put(api_url, json=payload) as resp:
            if resp.status not in (200, 201):
                error_text = await resp.text()
                raise RuntimeError(f"GitHub upload failed: {resp.status} - {error_text}")

    return f"{TRANSCRIPT_BASE_URL}/{path_in_repo}"