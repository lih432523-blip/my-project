"""Integration boundary tests run without Streamlit, Torch, or an LLM server."""
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.frontend.service import BackendService, FrontendError, normalize_result, typewriter
from src.frontend.state import SessionStore, markdown_export


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.owner = uuid.uuid4().hex
        self.store = SessionStore(self.tmp.name, self.owner)

    def test_round_trip_switch_delete_and_export(self):
        state = self.store.load()
        first = state["active_id"]
        self.store.append(state, "user", "论文的方法是什么？")
        result = {"sources": [{"source": "a.pdf", "page": 3}], "trace": [{"action": "search"}]}
        self.store.append(state, "assistant", "## 方法\n根据原文回答。", result)
        second = self.store.create(state)
        loaded = SessionStore(self.tmp.name, self.owner).load()
        self.assertEqual(loaded["active_id"], second)
        self.assertEqual(loaded["sessions"][first]["messages"][1]["result"], result)
        export = markdown_export(loaded["sessions"][first])
        self.assertIn("a.pdf", export)
        self.assertIn("第 3 页", export)
        self.store.delete(loaded, second)
        self.assertEqual(self.store.load()["active_id"], first)
        self.store.delete(loaded, first)
        self.assertEqual(len(self.store.load()["sessions"]), 1)
        self.assertNotIn(first, self.store.load()["sessions"])

    def test_owners_are_isolated_and_corrupt_file_is_preserved(self):
        state = self.store.load()
        self.store.append(state, "user", "private")
        other = SessionStore(self.tmp.name, uuid.uuid4().hex).load()
        self.assertEqual(other["sessions"][other["active_id"]]["messages"], [])
        self.store.path.write_text("broken", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "原文件已保留"):
            self.store.load()
        self.assertEqual(self.store.path.read_text(), "broken")

    def test_owner_path_cannot_escape(self):
        with self.assertRaises(ValueError):
            SessionStore(self.tmp.name, "../../x")


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.backend = BackendService(self.root / "data", self.root / "runtime")
        from src.agent import observability
        log_patch = patch.object(observability, "LOG_PATH", str(self.root / "test_requests.jsonl"))
        log_patch.start()
        self.addCleanup(log_patch.stop)

    def test_upload_duplicates_and_recoverable_delete(self):
        data = b"%PDF-1.7\nexample"
        self.backend.upload("a.PDF", data)
        self.assertEqual(self.backend.documents()[0]["name"], "a.pdf")
        self.assertIn("跳过", self.backend.upload("a.pdf", data)["status"])
        with self.assertRaisesRegex(FrontendError, "同名"):
            self.backend.upload("a.pdf", data + b"changed")
        self.backend.ready_fingerprint = self.backend._fingerprint()
        self.assertEqual(self.backend.documents()[0]["status"], "已向量化")
        target = self.backend.delete_document("a.pdf")
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(self.backend.documents(), [])
        self.assertIsNone(self.backend.ready_fingerprint)
        self.assertFalse((self.root / "data/a.pdf").exists())

    def test_invalid_files_and_path_traversal(self):
        for name, data in [("../../escape.pdf", b"%PDF-1.7"), ("x.txt", b"%PDF-1.7"),
                           ("bad.pdf", b"not pdf"), ("empty.pdf", b"")]:
            with self.subTest(name=name), self.assertRaises(FrontendError):
                self.backend.upload(name, data)
        self.backend.data_dir.mkdir()
        outside = self.root / "outside.pdf"
        outside.write_bytes(b"%PDF-1.7")
        (self.backend.data_dir / "linked.pdf").symlink_to(outside)
        self.assertEqual(self.backend.documents(), [])
        with self.assertRaises(FrontendError):
            self.backend.read_document("linked.pdf")
        with self.assertRaises(FrontendError):
            self.backend.delete_document("linked.pdf")
        self.assertTrue(outside.exists())

    def test_upload_size_limit(self):
        with patch("src.frontend.service.MAX_UPLOAD_BYTES", 8):
            with self.assertRaisesRegex(FrontendError, "50 MB"):
                self.backend.upload("big.pdf", b"%PDF-1.7more")

    def test_real_agent_time_route_does_not_load_models(self):
        result = self.backend.chat("现在几点？", uuid.uuid4().hex, use_memory=False)
        self.assertTrue(result["success"])
        self.assertEqual(result["tools_used"], ["current_time"])
        self.assertIn("当前系统时间", result["answer"])
        self.assertFalse(self.backend.data_dir.exists())
        from src import generation
        self.assertIsNone(generation._rag_instance)

    def test_empty_corpus_and_long_question(self):
        with self.assertRaisesRegex(FrontendError, "知识库为空"):
            self.backend.chat("论文有哪些方法？", uuid.uuid4().hex)
        with self.assertRaisesRegex(FrontendError, "不能为空"):
            self.backend.chat("  ", uuid.uuid4().hex)
        with self.assertRaisesRegex(FrontendError, "过长"):
            self.backend.chat("问" * 12001, uuid.uuid4().hex)

    def test_index_failure_and_success_are_distinct(self):
        self.backend.upload("a.pdf", b"%PDF-1.7test")
        from src.agent import tools
        class PDF:
            pages = [SimpleNamespace(extract_text=lambda: "paper text")]
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        with patch.dict(sys.modules, {"pdfplumber": SimpleNamespace(open=lambda path: PDF())}):
            with patch.object(tools, "refresh_knowledge_base", side_effect=RuntimeError("embedding failed")):
                with self.assertRaisesRegex(FrontendError, "embedding failed"):
                    self.backend.build_index()
            self.assertEqual(self.backend.documents()[0]["status"], "建库失败，可重试")
            self.assertFalse(self.backend.manifest_path.exists())
            with patch.object(tools, "refresh_knowledge_base", return_value=8):
                self.assertEqual(self.backend.build_index(), 8)
        self.assertEqual(self.backend.documents()[0]["status"], "已向量化")
        new_service = BackendService(self.backend.data_dir, self.backend.runtime_dir)
        self.assertEqual(new_service.documents()[0]["status"], "待恢复索引")
        self.backend.upload("b.pdf", b"%PDF-1.7second")
        self.assertNotEqual(self.backend.documents()[0]["status"], "已向量化")

    def test_scanned_pdf_is_not_marked_indexed(self):
        self.backend.upload("scan.pdf", b"%PDF-1.7test")
        class PDF:
            pages = [SimpleNamespace(extract_text=lambda: "")]
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        with patch.dict(sys.modules, {"pdfplumber": SimpleNamespace(open=lambda path: PDF())}):
            with self.assertRaisesRegex(FrontendError, "OCR"):
                self.backend.build_index()
        self.assertEqual(self.backend.documents()[0]["status"], "建库失败，可重试")

    def test_memory_rehydrates_and_clear_does_not_affect_other_session(self):
        from src.agent.memory import get_memory_stats, clear_memory
        first, second = uuid.uuid4().hex, uuid.uuid4().hex
        self.addCleanup(clear_memory, first)
        self.addCleanup(clear_memory, second)
        history = [
            {"role": "user", "content": "介绍论文"},
            {"role": "assistant", "content": "论文介绍", "result": {
                "memory_stats": {"active_paper": "Attention Is All You Need"}}},
        ]
        self.backend._restore_memory(first, history)
        self.backend._restore_memory(first, history)
        self.backend.chat("现在几点？", second)
        self.assertEqual(get_memory_stats(first)["total_messages"], 2)
        self.assertEqual(get_memory_stats(first)["active_paper"], "Attention Is All You Need")
        self.backend.clear_session(first)
        self.assertEqual(get_memory_stats(first)["total_messages"], 0)
        self.assertEqual(get_memory_stats(second)["total_messages"], 2)

    def test_sources_unknown_metrics_and_stream_text_preserved(self):
        value = {"answer": "## 方法\n中文 **Markdown**", "success": True,
                 "sources": [{"source": "a.pdf", "page": 1, "rerank_score": None},
                             {"source": "a.pdf", "page": 1}, None], "trace": [None]}
        normalized = normalize_result(value)
        self.assertEqual(len(normalized["sources"]), 1)
        self.assertEqual(normalized["trace"], [])
        self.assertIsNone(normalized["timing"]["total_time"])
        self.assertEqual("".join(typewriter(value["answer"], enabled=False)), value["answer"])


if __name__ == "__main__":
    unittest.main()
