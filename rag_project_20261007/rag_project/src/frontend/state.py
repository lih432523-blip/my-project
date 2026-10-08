"""Persistent browser workspace. No backend/model imports in this module."""
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class SessionStore:
    def __init__(self, directory, owner_id):
        # A random UUID identifies a browser workspace, never a filesystem path.
        self.owner_id = uuid.UUID(str(owner_id)).hex
        self.path = Path(directory) / (self.owner_id + ".json")
        self.lock = RLock()

    def load(self):
        with self.lock:
            if not self.path.exists():
                state = {"active_id": None, "sessions": {}}
                self.create(state)
                return state
            try:
                state = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(state.get("sessions"), dict):
                    raise ValueError("sessions must be a mapping")
                for session_id, session in state["sessions"].items():
                    uuid.UUID(session_id)
                    if session.get("id") != session_id or not isinstance(session.get("messages"), list):
                        raise ValueError("invalid session")
                if not state["sessions"]:
                    self.create(state)
                elif state.get("active_id") not in state["sessions"]:
                    state["active_id"] = next(iter(state["sessions"]))
                return state
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ValueError(f"会话文件无法读取，原文件已保留：{self.path}") from exc

    def save(self, state):
        with self.lock:
            atomic_json(self.path, state)

    def create(self, state):
        session_id = uuid.uuid4().hex
        state["sessions"][session_id] = {
            "id": session_id, "title": "新会话", "created_at": now(),
            "updated_at": now(), "messages": [], "use_memory": True,
        }
        state["active_id"] = session_id
        self.save(state)
        return session_id

    def delete(self, state, session_id):
        if session_id not in state["sessions"]:
            raise ValueError("会话不存在")
        del state["sessions"][session_id]
        if state["active_id"] == session_id:
            state["active_id"] = next(iter(state["sessions"]), None)
        if not state["sessions"]:
            self.create(state)
        else:
            self.save(state)

    def append(self, state, role, content, result=None):
        session = state["sessions"][state["active_id"]]
        message = {"role": role, "content": content, "created_at": now()}
        if result is not None:
            message["result"] = result
        session["messages"].append(message)
        session["updated_at"] = now()
        if role == "user" and session["title"] == "新会话":
            session["title"] = content[:24] + ("…" if len(content) > 24 else "")
        self.save(state)


def markdown_export(session):
    lines = [f"# {session['title']}", "", f"创建时间：{session['created_at']}", ""]
    for message in session["messages"]:
        lines.extend(["## " + ("用户" if message["role"] == "user" else "科研助理"), "", message["content"], ""])
        for source in message.get("result", {}).get("sources", []):
            lines.append(f"- 引用：{source.get('source', '未知文档')}，第 {source.get('page', '?')} 页")
        lines.append("")
    return "\n".join(lines)
