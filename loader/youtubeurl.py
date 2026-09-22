import re
from urllib.parse import parse_qs, urlparse

from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi


YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_video_id(video_url: str) -> str:
    url = video_url.strip()

    if YOUTUBE_ID_PATTERN.match(url):
        return url

    parsed_url = urlparse(url)
    host = parsed_url.netloc.lower()
    path_parts = [
        part
        for part in parsed_url.path.split("/")
        if part
    ]

    if host.endswith("youtu.be") and path_parts:
        video_id = path_parts[0]
    elif "youtube.com" in host:
        query_video_id = parse_qs(parsed_url.query).get("v")

        if query_video_id:
            video_id = query_video_id[0]
        elif path_parts and path_parts[0] in {"embed", "shorts", "live"}:
            video_id = path_parts[1] if len(path_parts) > 1 else ""
        else:
            video_id = ""
    else:
        video_id = ""

    if not YOUTUBE_ID_PATTERN.match(video_id):
        raise ValueError("Invalid YouTube URL or video id.")

    return video_id


def _snippet_text(snippet) -> str:
    if isinstance(snippet, dict):
        return snippet.get("text", "")

    return getattr(snippet, "text", "")


def load_youtube_url(video_url: str, languages: list[str] | None = None):
    video_id = extract_youtube_video_id(video_url)
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)

    available_transcripts = list(transcript_list)

    if not available_transcripts:
        raise ValueError("No transcript is available for this YouTube video.")

    if languages:
        try:
            selected_transcript = transcript_list.find_transcript(languages)
        except Exception as exc:
            available_languages = ", ".join(
                transcript.language_code for transcript in available_transcripts
            )
            raise ValueError(
                "None of the requested transcript languages are available. "
                f"Available languages: {available_languages}."
            ) from exc
    else:
        manual_transcripts = [
            transcript
            for transcript in available_transcripts
            if not getattr(transcript, "is_generated", False)
        ]
        selected_transcript = (manual_transcripts or available_transcripts)[0]

    transcript = selected_transcript.fetch()
    transcript_text = "\n".join(
        text
        for text in (
            _snippet_text(snippet).strip()
            for snippet in transcript
        )
        if text
    )

    if not transcript_text.strip():
        raise ValueError(
            "The YouTube transcript is empty. Try a video that has captions enabled."
        )

    return [
        Document(
            page_content=transcript_text,
            metadata={
                "source": video_url,
                "video_id": video_id,
                "language": getattr(selected_transcript, "language_code", None),
            },
        )
    ], video_id
