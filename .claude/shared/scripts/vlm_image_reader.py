#!/usr/bin/env python3
"""
VLM Image Reader — Direct vision API call for PNG/JPEG analysis.

Bypasses the Read tool's model capability gate by calling the vision model API
directly with an inline base64 image payload.

Usage:
    python vlm_image_reader.py <image_path> [question] [--model MODEL] [--json]

Environment variables (with defaults):
    VISION_API_URL   default: https://api.llm.ustc.edu.cn/v1/chat/completions
    VISION_API_KEY   REQUIRED — set via environment variable
    VISION_MODEL     default: qwen3.6-reasoner

Exit codes:
    0  success — model description printed to stdout
    1  usage error
    2  API error (non-200 or parse failure)
    3  file error (missing / unreadable / too large)
"""

import sys
import json
import base64
import urllib.request
import urllib.error
import os
import mimetypes

MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MiB

DEFAULT_QUESTION = (
    "You are an industrial process diagnostician analyzing a data visualization chart. "
    "Describe in detail: (1) chart type, (2) title, (3) X/Y axis labels and ranges, "
    "(4) legend/categories and colors, (5) overall trend direction and magnitude, "
    "(6) any outliers, anomalies, or notable patterns, "
    "(7) temporal alignment between parameters if multiple are shown. "
    "Be specific with values and time points."
)

MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def detect_mime(image_path):
    ext = os.path.splitext(image_path)[1].lower()
    if ext in MIME_BY_EXT:
        return MIME_BY_EXT[ext]
    # Fallback: sniff header bytes
    with open(image_path, "rb") as f:
        header = f.read(16)
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"  # safe default


def read_image(image_path, question=None, model=None):
    api_url = os.environ.get(
        "VISION_API_URL",
        "https://api.llm.ustc.edu.cn/v1/chat/completions",
    )
    api_key = os.environ.get("VISION_API_KEY")
    if not api_key:
        print("ERROR: VISION_API_KEY environment variable not set. Set it to your vision model API key.", file=sys.stderr)
        print("       Example: export VISION_API_KEY=sk-your-key-here", file=sys.stderr)
        sys.exit(2)
    model = model or os.environ.get("VISION_MODEL", "qwen3.6-reasoner")
    question = question or DEFAULT_QUESTION

    if not os.path.exists(image_path):
        print(f"ERROR: file not found: {image_path}", file=sys.stderr)
        sys.exit(3)

    file_size = os.path.getsize(image_path)
    if file_size > MAX_IMAGE_BYTES:
        print(
            f"ERROR: image too large: {file_size} bytes (max {MAX_IMAGE_BYTES})",
            file=sys.stderr,
        )
        sys.exit(3)

    mime = detect_mime(image_path)

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{img_b64}"},
                    },
                ],
            }
        ],
        "max_tokens": int(os.environ.get("VISION_MAX_TOKENS", "4096")),
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=int(os.environ.get("VISION_TIMEOUT", "180"))) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: API returned HTTP {e.code}: {err_body[:500]}", file=sys.stderr)
        sys.exit(2)
    except urllib.error.URLError as e:
        print(f"ERROR: network error: {e.reason}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON response: {e}", file=sys.stderr)
        sys.exit(2)

    if "error" in result:
        print(
            f"ERROR: API error: {result['error'].get('message', result['error'])}",
            file=sys.stderr,
        )
        sys.exit(2)

    choices = result.get("choices", [])
    if not choices:
        print("ERROR: no choices in API response", file=sys.stderr)
        sys.exit(2)

    message = choices[0].get("message", {}) or {}
    content = message.get("content", "")
    reasoning = message.get("reasoning_content", "")

    # Reasoning models (e.g. qwen3.6-reasoner) may exhaust max_tokens during
    # the reasoning phase, leaving content=None. Fall back to reasoning so the
    # caller still gets usable visual analysis.
    if not content and reasoning:
        content = reasoning
        finish = f"{finish} (reasoning_fallback)"

    return {
        "content": content,
        "reasoning": reasoning,
        "model": result.get("model", model),
        "finish_reason": finish,
        "usage": result.get("usage", {}),
    }


def main():
    args = sys.argv[1:]
    if not args:
        print(
            "Usage: python vlm_image_reader.py <image_path> [question] [--model MODEL] [--json]",
            file=sys.stderr,
        )
        sys.exit(1)

    image_path = args[0]
    question = None
    model = None
    output_json = False

    i = 1
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif args[i] == "--json":
            output_json = True
            i += 1
        elif question is None:
            question = args[i]
            i += 1
        else:
            question += " " + args[i]
            i += 1

    result = read_image(image_path, question, model)

    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["content"])
        if result.get("reasoning"):
            print("\n--- reasoning_content ---", file=sys.stderr)
            print(result["reasoning"][:500], file=sys.stderr)


if __name__ == "__main__":
    main()
