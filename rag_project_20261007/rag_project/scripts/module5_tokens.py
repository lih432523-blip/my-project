"""Capture actual Ollama token counts during serial, single-process evaluations.

This wrapper observes responses already requested by the evaluated code. It does
not send requests, estimate counts, consume streaming iterators, or change core
Agent/RAG files. Use ``with TokenCapture() as capture: ...`` then ``summary()``.
Incomplete measurements return ``None`` for the aggregate token fields.
"""
import json
from collections.abc import Mapping
from urllib.parse import urlsplit
import urllib.request


_active_capture = None


def _count(value):
    """Only accept actual, nonnegative integer count fields."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _error(exception):
    return f"{type(exception).__name__}: {exception}"[:500]


class _ResponseProxy:
    """Delegate the response while observing bytes returned by its own read()."""

    def __init__(self, response, capture, record):
        self._response = response
        self._capture = capture
        self._record = record
        self._parts = []

    def __getattr__(self, name):
        return getattr(self._response, name)

    def __iter__(self):
        return iter(self._response)

    def __next__(self):
        return next(self._response)

    def __enter__(self):
        try:
            entered = self._response.__enter__()
        except Exception as exc:
            self._capture._failed(self._record, exc)
            raise
        if entered is self._response:
            return self
        return _ResponseProxy(entered, self._capture, self._record)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self._response.__exit__(exc_type, exc_value, traceback)
        except Exception as exc:
            self._capture._failed(self._record, exc)
            raise

    def read(self, *args, **kwargs):
        try:
            raw = self._response.read(*args, **kwargs)
        except Exception as exc:
            self._capture._failed(self._record, exc)
            raise
        # A caller may perform partial reads. Accumulate only bytes it requested,
        # without advancing the response or replacing its return value.
        if not self._record.get("failed") and not self._record["complete"]:
            try:
                if isinstance(raw, bytes):
                    self._parts.append(raw)
                    payload = b"".join(self._parts)
                elif isinstance(raw, str):
                    self._parts.append(raw)
                    payload = "".join(self._parts)
                else:
                    payload = None
                if payload:
                    self._capture._observe(self._record, json.loads(payload))
            except (TypeError, ValueError, UnicodeError):
                # A partial, malformed or streaming response stays incomplete.
                pass
        return raw


class TokenCapture:
    """Temporarily observe urllib Agent calls and nonstreaming ollama.chat calls.

    Patches process-wide functions, so contexts must not overlap and evaluations
    must run serially. The original functions are restored even when the body
    raises. An empty successful operation has a complete zero-token measurement;
    the evaluator must separately mark failed backend operations incomplete.
    """

    def __init__(self):
        self.records = []
        self._entered = False
        self._urlopen_original = None
        self._ollama_module = None
        self._ollama_chat_original = None

    def _record(self, backend, model=None):
        record = {
            "call": len(self.records) + 1,
            "backend": backend,
            "model": model,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "complete": False,
            "error": "Response token count fields have not been captured.",
        }
        self.records.append(record)
        return record

    def _failed(self, record, exception):
        record.update(complete=False, failed=True, error=_error(exception))

    def _observe(self, record, value):
        if record.get("failed"):
            return
        if not isinstance(value, Mapping):
            dump = getattr(value, "model_dump", None)
            value = dump() if callable(dump) else None
        if not isinstance(value, Mapping):
            record["error"] = "Response does not expose token count fields."
            return
        prompt = _count(value.get("prompt_eval_count"))
        completion = _count(value.get("eval_count"))
        complete = prompt is not None and completion is not None
        record.update(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion if complete else None,
            complete=complete,
            error=None if complete else "Missing or invalid prompt_eval_count/eval_count.",
        )

    def _urlopen(self, url, *args, **kwargs):
        try:
            address = url.full_url if hasattr(url, "full_url") else str(url)
            is_chat = urlsplit(address).path == "/api/chat"
        except (TypeError, ValueError):
            is_chat = False
        if not is_chat:
            return self._urlopen_original(url, *args, **kwargs)
        data = getattr(url, "data", None)
        if data is None:
            data = kwargs.get("data", args[0] if args else None)
        try:
            request_body = json.loads(data) if data else {}
        except (TypeError, ValueError, UnicodeError):
            request_body = {}
        if not isinstance(request_body, dict):
            request_body = {}
        record = self._record("urllib", request_body.get("model"))
        record["url"] = address
        try:
            response = self._urlopen_original(url, *args, **kwargs)
        except Exception as exc:
            self._failed(record, exc)
            raise
        if request_body.get("stream") is True:
            record["error"] = "Streaming token measurement is unsupported; response was not consumed."
            return response
        return _ResponseProxy(response, self, record)

    def _ollama_chat(self, *args, **kwargs):
        model = kwargs.get("model", args[0] if args else None)
        record = self._record("ollama.chat", model)
        try:
            response = self._ollama_chat_original(*args, **kwargs)
        except Exception as exc:
            self._failed(record, exc)
            raise
        if kwargs.get("stream") is True:
            record["error"] = "Streaming token measurement is unsupported; iterator was not consumed."
            return response
        try:
            self._observe(record, response)
        except Exception as exc:
            # Instrumentation errors must not alter the backend response.
            record.update(complete=False, error="Token capture failed: " + _error(exc))
        return response

    def __enter__(self):
        global _active_capture
        if self._entered or _active_capture is not None:
            raise RuntimeError("TokenCapture contexts must run serially and cannot overlap.")
        self.records = []
        try:
            import ollama
        except ImportError:
            ollama = None
        self._urlopen_original = urllib.request.urlopen
        self._ollama_module = ollama
        self._ollama_chat_original = getattr(ollama, "chat", None)
        _active_capture = self
        self._entered = True
        try:
            urllib.request.urlopen = self._urlopen
            if callable(self._ollama_chat_original):
                ollama.chat = self._ollama_chat
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        global _active_capture
        if self._entered:
            try:
                urllib.request.urlopen = self._urlopen_original
            finally:
                try:
                    if callable(self._ollama_chat_original):
                        self._ollama_module.chat = self._ollama_chat_original
                finally:
                    self._entered = False
                    _active_capture = None
        return False

    def summary(self):
        measured = [record for record in self.records if record["complete"]]
        complete = len(measured) == len(self.records)
        known_total = sum(record["total_tokens"] for record in measured)
        return {
            "prompt_tokens": sum(record["prompt_tokens"] for record in measured) if complete else None,
            "completion_tokens": sum(record["completion_tokens"] for record in measured) if complete else None,
            "total_tokens": known_total if complete else None,
            "calls": len(self.records),
            "measured_calls": len(measured),
            "complete": complete,
            "known_total_tokens": known_total,
            "records": [dict(record) for record in self.records],
        }
