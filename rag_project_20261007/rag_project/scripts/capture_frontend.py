"""Capture actual Streamlit pages. Requires a running app and Playwright.

python scripts/capture_frontend.py --with-rag
No simulated answers or generated mockup images are used.
"""
import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--output", default="docs/screenshots")
    parser.add_argument("--browser-channel", default="chrome", help="Use installed Chrome; use chromium if installed through Playwright")
    parser.add_argument("--with-rag", action="store_true", help="Run a real paper query; requires C/D models and Ollama")
    parser.add_argument("--timeout", type=int, default=600000, help="Timeout in milliseconds for model/index operations")
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError:
        raise SystemExit("先安装：python -m pip install -r requirements-checks.txt")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    shots = []
    workspace = uuid.uuid4().hex
    separator = "&" if "?" in args.url else "?"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.browser_channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
        page.set_default_timeout(30000)
        page.goto(args.url + separator + "workspace=" + workspace)
        expect(page.get_by_role("heading", name="把论文，变成可以对话的知识。")).to_be_visible()

        def shot(name):
            page.screenshot(path=str(output / name), full_page=True)
            shots.append(name)

        shot("01-workspace.png")
        sidebar = page.get_by_test_id("stSidebar")
        sidebar.get_by_role("tab", name="文档管理").click()
        sidebar.locator("details").filter(has_text="attention_is_all_you_need.pdf").first.locator("summary").click()
        shot("02-document-management.png")
        question = page.get_by_role("textbox", name="询问论文的方法、数据集、实验结果，或比较两篇论文…")
        question.fill("现在几点？")
        question.press("Enter")
        expect(page.get_by_test_id("stChatMessage").last).to_contain_text("当前系统时间", timeout=30000)
        page.locator("details").filter(has_text="Agent 执行过程").last.locator("summary").click()
        shot("03-chat-and-agent.png")
        if args.with_rag:
            question.fill("《Attention Is All You Need》的作者是谁？")
            question.press("Enter")
            latest = page.get_by_test_id("stChatMessage").last
            expect(latest).to_contain_text("Paper Metadata", timeout=args.timeout)
            expect(latest).to_contain_text("引用来源", timeout=args.timeout)
            shot("04-paper-answer-and-citations.png")
        sidebar.get_by_role("tab", name="历史会话").click()
        page.locator("details").filter(has_text="系统状态与运行统计").last.locator("summary").click()
        shot("05-history-and-system-status.png")
        browser.close()
    (output / "capture-record.json").write_text(json.dumps({
        "captured_at": datetime.now().astimezone().isoformat(), "url": args.url,
        "workspace": workspace, "real_rag_query": args.with_rag, "screenshots": shots,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已从运行中的界面截取 {len(shots)} 张图片，保存在 {output}")


if __name__ == "__main__":
    main()
