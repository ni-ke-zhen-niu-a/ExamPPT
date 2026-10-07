from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import sys

from . import __version__
from .core.layout_engine import build as build_ppt
from .core.pdf_splitter import save_scan_result, scan_pdf


def doctor() -> int:
    print(f"ExamPPT {__version__}")
    print(f"Python: {platform.python_version()}")
    print(f"System: {platform.system()} {platform.release()} {platform.machine()}")
    if os.name != "nt":
        print("Status: V0.1 targets Windows 10/11 x64.")
        return 1

    try:
        import pdfplumber  # noqa: F401
        import pypdfium2  # noqa: F401
        import pptx  # noqa: F401
        from PIL import Image  # noqa: F401
        print("Core dependencies: OK")
    except Exception as exc:
        print(f"Core dependencies: FAIL ({exc})")
        return 2

    print("PPTX generation: available (PowerPoint/WPS not required for generation)")
    print("PowerPoint/WPS playback QA: adapter under development")
    return 0


def _default_workdir(pdf_path: Path, out_dir: str | None) -> Path:
    if out_dir:
        return Path(out_dir).resolve()
    return pdf_path.parent / f"{pdf_path.stem}_ExamPPT"


def scan_command(args) -> int:
    pdf_path = Path(args.pdf).resolve()
    workdir = _default_workdir(pdf_path, args.out_dir)
    workdir.mkdir(parents=True, exist_ok=True)

    result = scan_pdf(pdf_path, output_dir=workdir, render=not args.no_render, dpi=args.dpi)
    if getattr(args, "title", None):
        result.name = args.title
    manifest_path = workdir / "manifest.json"
    save_scan_result(result, manifest_path)

    summary = {
        "status": result.status,
        "source_pdf": str(pdf_path),
        "question_count": len(result.questions),
        "cross_page_questions": [q.number for q in result.questions if q.cross_page],
        "sections": [
            {"title": s.title, "start_question": s.start_question}
            for s in result.sections
        ],
        "warnings": result.warnings,
        "manifest": str(manifest_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.status == "PASS" else 3


def build_command(args) -> int:
    pdf_path = Path(args.pdf).resolve()
    workdir = _default_workdir(pdf_path, args.out_dir)
    workdir.mkdir(parents=True, exist_ok=True)

    result = scan_pdf(pdf_path, output_dir=workdir, render=True, dpi=args.dpi)
    if getattr(args, "title", None):
        result.name = args.title
    manifest_path = workdir / "manifest.json"
    save_scan_result(result, manifest_path)

    pptx_path = workdir / f"{pdf_path.stem}_讲题版.pptx"
    qa_path = workdir / "qa.json"
    report = build_ppt(
        manifest_path=manifest_path,
        output_pptx=pptx_path,
        qa_json=qa_path,
    )

    combined_status = (
        "PASS"
        if result.status == "PASS" and report["status"] == "PASS"
        else "MANUAL_REQUIRED"
    )
    summary = {
        "status": combined_status,
        "scan_status": result.status,
        "layout_status": report["status"],
        "question_count": len(result.questions),
        "cross_page_questions": [q.number for q in result.questions if q.cross_page],
        "pptx": str(pptx_path),
        "manifest": str(manifest_path),
        "qa": str(qa_path),
        "warnings": result.warnings,
        "violations": report["violations"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if combined_status == "PASS" else 3


def main() -> int:
    parser = argparse.ArgumentParser(prog="exam-ppt", description="PDF试卷无损转PPT 工具")
    parser.add_argument("--version", action="version", version=f"ExamPPT {__version__}")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("doctor", help="检查本机运行环境")

    scan = sub.add_parser("scan", help="自动检测题目边界并生成 Question IR")
    scan.add_argument("pdf")
    scan.add_argument("--out-dir")
    scan.add_argument("--dpi", type=int, default=180)
    scan.add_argument("--no-render", action="store_true")
    scan.add_argument("--title", help="覆盖PPT页眉中的试卷名称")

    build = sub.add_parser("build", help="自动切题并生成课堂讲评 PPT")
    build.add_argument("pdf")
    build.add_argument("--out-dir")
    build.add_argument("--dpi", type=int, default=180)
    build.add_argument("--title", help="覆盖PPT页眉中的试卷名称")

    args = parser.parse_args()
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "scan":
        return scan_command(args)
    if args.cmd == "build":
        return build_command(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
