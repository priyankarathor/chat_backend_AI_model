from pathlib import Path


def read_text_file(file_path: str) -> str:
    data = Path(file_path).read_bytes()

    if data.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in data[:200]:
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass

    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="replace")
