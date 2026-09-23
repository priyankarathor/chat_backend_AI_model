import json
import os
import re
import tempfile
from html import unescape
from pathlib import Path
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


def _youtube_proxy_urls() -> tuple[str | None, str | None]:
    http_proxy = os.getenv("YOUTUBE_HTTP_PROXY") or os.getenv("HTTP_PROXY")
    https_proxy = os.getenv("YOUTUBE_HTTPS_PROXY") or os.getenv("HTTPS_PROXY")
    return http_proxy, https_proxy


def _create_youtube_api() -> YouTubeTranscriptApi:
    http_proxy, https_proxy = _youtube_proxy_urls()

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
    caption_error = None
    try:
        return _load_transcript_with_ytdlp(
            video_url,
            languages,
        )
    except Exception as exc:
        caption_error = exc

    try:
        return _transcribe_youtube_audio(video_url, languages)
    except Exception as audio_exc:
        raise ValueError(
            "YouTube blocked transcript requests from this server IP, "
            "and both caption and audio transcription fallbacks failed. "
            f"Caption error: {_safe_fallback_error(caption_error)} "
            f"Audio error: {_safe_fallback_error(audio_exc)}"
        ) from audio_exc


def _safe_fallback_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    proxy_urls = _youtube_proxy_urls()
    for proxy_url in proxy_urls:
        if proxy_url:
            message = message.replace(proxy_url, "<configured proxy>")

    if not message:
        return "unknown caption extraction error."

    lowered = message.lower()
    if "sign in to confirm" in lowered or "not a bot" in lowered:
        return (
            "YouTube requires authentication. Configure YOUTUBE_COOKIES_FILE "
            "with an exported YouTube cookies.txt file, or use "
            "YOUTUBE_HTTPS_PROXY, then restart the backend."
        )
    if "http error 429" in lowered or "too many requests" in lowered:
        return (
            "YouTube rate-limited this server (HTTP 429). Configure "
            "YOUTUBE_HTTPS_PROXY with a rotating residential proxy URL, then "
            "restart the backend."
        )
    if "http error 403" in lowered or "forbidden" in lowered:
        return (
            "YouTube denied the caption download (HTTP 403). Configure "
            "YOUTUBE_COOKIES_FILE or YOUTUBE_HTTPS_PROXY, then restart the backend."
        )
    if "no captions are available" in lowered:
        return "this video does not expose captions."

    return message[:300]


def _load_transcript_with_ytdlp(
    video_url: str,
    languages: list[str] | None = None,
) -> tuple[str, str | None]:
    from yt_dlp import YoutubeDL
    from yt_dlp.networking import Request

    http_proxy, https_proxy = _youtube_proxy_urls()
    proxy = https_proxy or http_proxy
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if proxy:
        options["proxy"] = proxy

    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies_file:
        cookie_path = Path(cookies_file).expanduser()
        if not cookie_path.is_file():
            raise ValueError(
                f"YOUTUBE_COOKIES_FILE does not exist: {cookie_path}"
            )
        options["cookiefile"] = str(cookie_path)

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

        # Reuse yt-dlp's opener so its cookies, headers, and proxy stay attached.
        request = Request(
            subtitle["url"],
            headers=subtitle.get("http_headers"),
            method="GET",
            extensions={"timeout": 30},
        )
        with downloader.urlopen(request) as response:
            events = json.loads(response.read()).get("events", [])
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


def _transcribe_youtube_audio(
    video_url: str,
    languages: list[str] | None = None,
) -> tuple[str, str | None]:
    from groq import Groq
    from yt_dlp import YoutubeDL

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is required for the audio fallback.")

    http_proxy, https_proxy = _youtube_proxy_urls()
    proxy = https_proxy or http_proxy
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    if proxy:
        options["proxy"] = proxy

    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies_file:
        cookie_path = Path(cookies_file).expanduser()
        if not cookie_path.is_file():
            raise ValueError(
                f"YOUTUBE_COOKIES_FILE does not exist: {cookie_path}"
            )
        options["cookiefile"] = str(cookie_path)

    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(video_url, download=False)

    supported_extensions = {
        "flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"
    }
    audio_formats = [
        item
        for item in info.get("formats", [])
        if item.get("url")
        and item.get("acodec") not in {None, "none"}
        and item.get("vcodec") == "none"
        and item.get("ext") in supported_extensions
    ]
    if not audio_formats:
        raise ValueError("YouTube did not expose a supported audio stream.")

    def audio_size(item: dict) -> float:
        size = item.get("filesize") or item.get("filesize_approx")
        if size:
            return float(size)

        duration = info.get("duration")
        bitrate = item.get("abr") or item.get("tbr")
        if duration and bitrate:
            return float(duration) * float(bitrate) * 125
        return float("inf")

    audio_format = min(
        audio_formats,
        key=lambda item: (audio_size(item), item.get("abr") or float("inf")),
    )
    max_audio_bytes = 24 * 1024 * 1024
    estimated_size = audio_size(audio_format)
    if estimated_size != float("inf") and estimated_size > max_audio_bytes:
        raise ValueError(
            "The smallest YouTube audio stream exceeds the 24 MB transcription limit."
        )

    http_proxy, https_proxy = _youtube_proxy_urls()
    proxies = None
    if http_proxy or https_proxy:
        proxies = {
            "http": http_proxy or https_proxy,
            "https": https_proxy or http_proxy,
        }
    transcription_args = {
        "model": os.getenv(
            "GROQ_TRANSCRIPTION_MODEL",
            "whisper-large-v3-turbo",
        ),
        "response_format": "json",
        "temperature": 0.0,
        "timeout": 90,
    }
    language = None
    if languages:
        requested_language = languages[0].split("-", 1)[0].lower()
        if re.fullmatch(r"[a-z]{2}", requested_language):
            transcription_args["language"] = requested_language
            language = requested_language

    suffix = f".{audio_format['ext']}"
    with tempfile.NamedTemporaryFile(suffix=suffix) as audio_file:
        with requests.get(
            audio_format["url"],
            headers=audio_format.get("http_headers"),
            proxies=proxies,
            allow_redirects=True,
            stream=True,
            timeout=60,
        ) as media_response:
            media_response.raise_for_status()
            downloaded_bytes = 0
            for chunk in media_response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                downloaded_bytes += len(chunk)
                if downloaded_bytes > max_audio_bytes:
                    raise ValueError(
                        "The YouTube audio stream exceeds the 24 MB transcription limit."
                    )
                audio_file.write(chunk)

        audio_file.flush()
        audio_file.seek(0)
        transcription = Groq(api_key=api_key).audio.transcriptions.create(
            file=(f"youtube{suffix}", audio_file.read()),
            **transcription_args,
        )
    transcript_text = getattr(transcription, "text", "").strip()
    if not transcript_text:
        raise ValueError("Groq returned an empty audio transcription.")

    return transcript_text, language or info.get("language")


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
