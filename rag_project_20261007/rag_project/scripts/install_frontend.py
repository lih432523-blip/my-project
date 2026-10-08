"""Install the A-only archive without overwriting any existing, different file.

python scripts/install_frontend.py --archive /path/member-A-server.tar.gz --target /root/autodl-tmp/rag_project
Add --apply after reviewing the dry-run output. No C/D backend modules are included.
"""
import argparse
import os
import tarfile
import tempfile
from pathlib import Path


ALLOWED = {
    "app.py", "src/config.py", "src/frontend/__init__.py", "src/frontend/state.py", "src/frontend/service.py",
    "requirements-frontend.txt", "requirements-checks.txt", ".streamlit/config.toml",
    "tests/test_frontend.py", "tests/test_streamlit_ui.py", "tests/test_server_handoff.py", "scripts/capture_frontend.py",
    "scripts/install_frontend.py", "docs/frontend_guide.md", "docs/member_A_implementation.md",
    "docs/member_A_validation.md", "docs/member_A_work_report.md", "docs/server_frontend_handoff.md",
}


def inspect_archive(archive, target):
    target = Path(target).expanduser().resolve()
    if not (target / "src/agent/agent.py").is_file() or not (target / "src/generation/__init__.py").is_file():
        raise ValueError("目标目录不包含 C/D 的 Agent 和 RAG 入口，请核对项目根目录。")
    entries = []
    seen = set()
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            if member.name not in ALLOWED or not member.isfile() or member.name in seen:
                raise ValueError(f"包中包含不允许安装的路径或文件类型：{member.name}")
            seen.add(member.name)
            destination = target / member.name
            if destination.is_symlink() or not destination.resolve().is_relative_to(target):
                raise ValueError(f"目标路径包含外部链接：{destination}")
            data = handle.extractfile(member).read()
            if destination.exists():
                if not destination.is_file() or destination.read_bytes() != data:
                    raise ValueError(f"已有不同内容，拒绝覆盖：{destination}。请先人工核对。")
                action = "相同，跳过"
            else:
                action = "新增"
            entries.append((destination, data, action))
    if seen != ALLOWED:
        raise ValueError("交付包文件不完整：" + ", ".join(sorted(ALLOWED - seen)))
    return entries


def install(entries):
    for destination, data, action in entries:
        if action != "新增":
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".install-a-", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.link(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        entries = inspect_archive(args.archive, args.target)
        for destination, data, action in entries:
            print(f"{action}: {destination}")
        if args.apply:
            install(entries)
            print("成员 A 文件已安装；C/D 原后端文件保持原样。")
        else:
            print("预检查完成，尚未写入；确认上述目标后可添加 --apply 执行。")
    except (ValueError, OSError, tarfile.TarError) as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
