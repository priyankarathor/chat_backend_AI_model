import os
import re
from html import unescape
from urllib.parse import parse_qs, urlparse

import requests
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    AgeRestricted,
    CouldNotRetrieveTranscript,
    IpBlocked,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api.proxies import GenericProxyConfig


YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _create_youtube_api() -> YouTubeTranscriptApi:
    http_proxy = os.getenv("YOUTUBE_HTTP_PROXY")
    https_proxy = os.getenv("YOUTUBE_HTTPS_PROXY")

    if not http_proxy and not https_proxy:
        return YouTubeTranscriptApi()

    return YouTubeTranscriptApi(
        proxy_config=GenericProxyConfig(
            http_url=http_proxy or https_proxy,
            https_url=https_proxy or http_proxy,
        )
    )


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


def _is_youtube_block_error(exc: Exception) -> bool:
    return isinstance(exc, (IpBlocked, RequestBlocked))


def _raise_readable_youtube_error(exc: Exception) -> None:
    if isinstance(exc, TranscriptsDisabled):
        raise ValueError(
            "No transcript is available because captions are disabled for this YouTube video."
        ) from exc

    if isinstance(exc, AgeRestricted):
        raise ValueError(
            "This YouTube video is age-restricted, so its transcript cannot be retrieved."
        ) from exc

    if isinstance(exc, VideoUnavailable):
        raise ValueError("This YouTube video is unavailable.") from exc

    if isinstance(exc, CouldNotRetrieveTranscript):
        raise ValueError(
            "Could not retrieve a transcript for this YouTube video. "
            "Try another captioned video or configure YOUTUBE_HTTPS_PROXY if YouTube "
            "is blocking this server."
        ) from exc

    raise exc


def _load_blocked_youtube_transcript(
    video_url: str,
    languages: list[str] | None,
):
    try:
        return _load_transcript_with_ytdlp(
            video_url,
            languages,
        )
    except Exception as fallback_exc:
        raise ValueError(
            "YouTube blocked transcript requests from this server IP, "
            "and the alternate caption method also failed. Change "
            "network or configure YOUTUBE_HTTPS_PROXY with a rotating "
            "residential proxy URL, then restart the backend."
        ) from fallback_exc


def _load_transcript_with_ytdlp(
    video_url: str,
    languages: list[str] | None = None,
) -> tuple[str, str | None]:
    from yt_dlp import YoutubeDL

    proxy = os.getenv("YOUTUBE_HTTPS_PROXY") or os.getenv("YOUTUBE_HTTP_PROXY")
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if proxy:
        options["proxy"] = proxy

    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(video_url, download=False)

    captions = {
        **(info.get("automatic_captions") or {}),
        **(info.get("subtitles") or {}),
    }
    preferred_languages = languages or ["en", "en-US", "en-GB", "hi"]
    language = next(
        (code for code in preferred_languages if captions.get(code)),
        next(iter(captions), None),
    )
    if not language:
        raise ValueError("No captions are available for this YouTube video.")

    formats = captions[language]
    subtitle = next(
        (item for item in formats if item.get("ext") == "json3"),
        None,
    )
    if not subtitle or not subtitle.get("url"):
        raise ValueError("No supported YouTube caption format is available.")

    response = requests.get(
        subtitle["url"],
        headers=subtitle.get("http_headers"),
        proxies={"http": proxy, "https": proxy} if proxy else None,
        timeout=30,
    )
    response.raise_for_status()
    events = response.json().get("events", [])
    lines = []
    for event in events:
        text = "".join(
            segment.get("utf8", "")
            for segment in event.get("segs", [])
        ).strip()
        if text:
            lines.append(unescape(text))

    transcript_text = "\n".join(lines)
    if not transcript_text.strip():
        raise ValueError("The YouTube captions are empty.")

    return transcript_text, language


def load_youtube_url(video_url: str, languages: list[str] | None = None):
    video_id = extract_youtube_video_id(video_url)
    api = _create_youtube_api()

    try:
        transcript_list = api.list(video_id)
    except Exception as exc:
        if _is_youtube_block_error(exc):
            transcript_text, language = _load_blocked_youtube_transcript(
                video_url,
                languages,
            )

            return [
                Document(
                    page_content=transcript_text,
                    metadata={
                        "source": video_url,
                        "video_id": video_id,
                        "language": language,
                    },
                )
            ], video_id

        _raise_readable_youtube_error(exc)

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

    try:
        transcript = selected_transcript.fetch()
    except Exception as exc:
        if _is_youtube_block_error(exc):
            transcript_text, language = _load_blocked_youtube_transcript(
                video_url,
                languages,
            )

            return [
                Document(
                    page_content=transcript_text,
                    metadata={
                        "source": video_url,
                        "video_id": video_id,
                        "language": language,
                    },
                )
            ], video_id

        _raise_readable_youtube_error(exc)

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
