"""Run after installing requirements-frontend.txt; uses real current_time tool."""
import importlib.util
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Streamlit not installed")
class StreamlitUITests(unittest.TestCase):
    def test_chat_history_switch_delete_and_reload(self):
        from streamlit.testing.v1 import AppTest
        from src.frontend.state import SessionStore
        with tempfile.TemporaryDirectory() as directory:
            with patch("src.config.RUNTIME_DIR", Path(directory)):
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
                owner = uuid.uuid4().hex
                app.query_params["workspace"] = owner
                app.run(timeout=20)
                self.assertFalse(app.exception)
                app.chat_input[0].set_value("现在几点？").run(timeout=20)
                self.assertFalse(app.exception)
                self.assertTrue(any("当前系统时间" in item.value for item in app.markdown))
                # A new session must hide the previous conversation.
                next(button for button in app.button if button.label == "＋ 新建会话").click().run(timeout=20)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.chat_message), 0)
                picker = next(select for select in app.selectbox if select.label == "历史会话")
                saved = SessionStore(Path(directory) / "sessions", owner).load()
                older = next(sid for sid, session in saved["sessions"].items() if session["messages"])
                picker.select(older).run(timeout=20)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.chat_message), 2)
                app.run(timeout=20)
                self.assertEqual(len(app.chat_message), 2)
                next(check for check in app.checkbox if check.label == "确认删除历史记录").check().run(timeout=20)
                next(button for button in app.button if button.label == "删除会话").click().run(timeout=20)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.chat_message), 0)
