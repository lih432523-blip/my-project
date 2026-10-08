"""Protect collaborator files during additive server installation."""
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.install_frontend import ALLOWED, inspect_archive, install


class ServerHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = self.root / "server"
        self.target.mkdir()
        for name in ("src/agent/agent.py", "src/generation/__init__.py"):
            file = self.target / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"collaborator backend")
        self.archive = self.root / "a.tar.gz"
        project = Path(__file__).resolve().parents[1]
        with tarfile.open(self.archive, "w:gz") as handle:
            for name in sorted(ALLOWED):
                handle.add(project / name, arcname=name)

    def test_dry_run_and_idempotent_install_keep_backend(self):
        entries = inspect_archive(self.archive, self.target)
        self.assertFalse((self.target / "app.py").exists())
        install(entries)
        self.assertTrue((self.target / "app.py").is_file())
        self.assertEqual((self.target / "src/agent/agent.py").read_bytes(), b"collaborator backend")
        again = inspect_archive(self.archive, self.target)
        self.assertTrue(all(action == "相同，跳过" for _, _, action in again))
        install(again)

    def test_conflict_rejects_all_writes(self):
        (self.target / "app.py").write_bytes(b"newer teammate frontend")
        with self.assertRaisesRegex(ValueError, "拒绝覆盖"):
            inspect_archive(self.archive, self.target)
        self.assertFalse((self.target / "src/config.py").exists())
        self.assertEqual((self.target / "app.py").read_bytes(), b"newer teammate frontend")

    def test_archive_cannot_escape_or_replace_backend(self):
        for name in ("../escape", "src/agent/agent.py"):
            with self.subTest(name=name):
                with tarfile.open(self.archive, "w:gz") as handle:
                    item = tarfile.TarInfo(name)
                    item.size = 3
                    handle.addfile(item, io.BytesIO(b"bad"))
                with self.assertRaisesRegex(ValueError, "不允许"):
                    inspect_archive(self.archive, self.target)
        self.assertEqual((self.target / "src/agent/agent.py").read_bytes(), b"collaborator backend")


if __name__ == "__main__":
    unittest.main()
