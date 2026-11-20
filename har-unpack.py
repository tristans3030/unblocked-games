import base64
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_SEGMENT_LEN = 120


def sanitize_segment(segment: str) -> str:
    cleaned = INVALID_WIN_CHARS.sub("_", segment).strip(" .")
    if len(cleaned) > MAX_SEGMENT_LEN:
        cleaned = cleaned[:MAX_SEGMENT_LEN].rstrip(" .")
    return cleaned or "_"


def safe_rel_path(url: str, mime_type: str | None) -> Path | None:
    parsed = urlparse(url)

    # Only unpack standard web URLs (skips data:, blob:, etc.)
    if parsed.scheme not in ("http", "https"):
        return None

    # Skip Cloudflare challenge/telemetry endpoints
    if "/cdn-cgi/" in parsed.path:
        return None

    host = sanitize_segment(parsed.netloc or "unknown-host")
    raw_path = parsed.path.lstrip("/")

    if not raw_path or raw_path.endswith("/"):
        raw_path = f"{raw_path}index.html"

    parts = [
        sanitize_segment(p)
        for p in raw_path.split("/")
        if p not in ("", ".", "..")
    ]
    if not parts:
        parts = ["index.html"]

    out_path = Path(host, *parts)

    if not out_path.suffix and mime_type:
        clean_mime = mime_type.split(";")[0].strip()
        ext = mimetypes.guess_extension(clean_mime)
        if ext and len(out_path.name + ext) <= MAX_SEGMENT_LEN:
            out_path = out_path.with_suffix(ext)

    return out_path


def unpack_har(har_file: str, output_dir: str = "har_unpacked") -> None:
    data = json.loads(Path(har_file).read_text(encoding="utf-8"))
    entries = data.get("log", {}).get("entries", [])
    base_out = Path(output_dir)
    saved_count = 0
    skipped_count = 0

    for entry in entries:
        status = entry.get("response", {}).get("status", 0)
        url = entry.get("request", {}).get("url", "")
        content = entry.get("response", {}).get("content", {})
        text = content.get("text")

        if status != 200 or not url or text is None:
            print(f"Skip (status {status}): {url}")
            skipped_count += 1
            continue

        rel_path = safe_rel_path(url, content.get("mimeType"))
        if rel_path is None:
            print(f"Skip (status {status}): {url}")
            skipped_count += 1
            continue

        if content.get("encoding") == "base64":
            payload = base64.b64decode(text)
        else:
            payload = text.encode("utf-8")

        target = base_out / rel_path

        if target.exists() and target.is_dir():
            target = target / "index.html"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        saved_count += 1

    print(f"Unpacked {saved_count} files into '{base_out}' (skipped {skipped_count} entries).")


if __name__ == "__main__":
    unpack_har("download.har")