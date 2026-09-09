"""Minimal configurable chat-completions transport; no SDK required."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from .io import fingerprint, write_json


class Provider:
    def __init__(self, model=None, cache_dir=".cache/llm", base_url=None):
        self.key = os.environ.get("LLM_API_KEY")
        self.model = model or os.environ.get("LLM_MODEL")
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL", "")).rstrip("/")
        self.cache_dir = Path(cache_dir)
        if not self.model or not self.base_url:
            raise ValueError(
                "Set LLM_MODEL and LLM_BASE_URL for live calls. LLM_API_KEY is required by hosted providers."
            )
        if not self.base_url.startswith("https://") and not self.base_url.startswith(
            ("http://localhost:", "http://127.0.0.1:")
        ):
            raise ValueError(
                "Use HTTPS for hosted endpoints or localhost for a local model."
            )

    def complete(self, system, payload):
        request = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        }
        cache = self.cache_dir / (
            fingerprint({"endpoint": self.base_url, "request": request}) + ".json"
        )
        if cache.exists():
            result = json.loads(cache.read_text(encoding="utf-8"))
            return {**result, "cache_hit": True, "latency_seconds": 0}
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        start = time.perf_counter()
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    self.base_url + "/chat/completions",
                    data=json.dumps(request).encode(),
                    headers=headers,
                )
                with urllib.request.urlopen(req, timeout=45) as response:
                    raw = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(
                        f"Model endpoint returned HTTP {error.code}"
                    ) from None
                time.sleep(2**attempt)
        content = raw["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = {
            "output": json.loads(content),
            "usage": raw.get("usage", {}),
            "model": raw.get("model", self.model),
            "latency_seconds": time.perf_counter() - start,
            "cache_hit": False,
        }
        write_json(cache, result)
        return result
