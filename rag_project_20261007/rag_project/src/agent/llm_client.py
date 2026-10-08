import json
import urllib.request
import urllib.error


OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:7b"


def chat(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    timeout: int = 120,
    json_mode: bool = False,
) -> str:
    """
    统一调用本地 Ollama Qwen2.5。

    json_mode=True 时，
    要求 Ollama 尽量返回合法 JSON。
    """

    import json
    import urllib.request
    import urllib.error

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    # JSON 结构化输出
    if json_mode:
        payload["format"] = "json"

    data = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as e:

        try:
            body = e.read().decode(
                "utf-8",
                errors="ignore",
            )
        except Exception:
            body = ""

        raise RuntimeError(
            f"Ollama HTTP Error: "
            f"{e.code}, {body}"
        )

    except urllib.error.URLError as e:

        raise RuntimeError(
            f"Ollama connection failed: {e}"
        )

    except TimeoutError:

        raise RuntimeError(
            "Ollama request timed out"
        )

    try:

        return (
            result["message"]["content"]
            .strip()
        )

    except (KeyError, TypeError) as e:

        raise RuntimeError(
            f"Invalid Ollama response: {result}"
        ) from e