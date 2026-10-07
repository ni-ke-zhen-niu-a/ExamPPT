from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import sys

from . import __version__
from .core.layout_engine import build as build_ppt
from .core.pdf_splitter import load_boundary_overrides, save_scan_result, scan_pdf
from .core.preview_renderer import render_slide_previews


def _configure_utf8_stdio() -> None:
    """Keep machine-readable CLI JSON valid when stdout/stderr are piped on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _emit_progress(percent: int, stage: str, detail: str = "") -> None:
    payload = {
        "percent": max(0, min(100, int(percent))),
        "stage": stage,
        "detail": detail,
    }
    print(
        "EXAMPPT_PROGRESS:" + json.dumps(payload, ensure_ascii=False),
        file=sys.stderr,
        flush=True,
    )


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

    result = scan_pdf(
        pdf_path,
        output_dir=workdir,
        render=not args.no_render,
        dpi=args.dpi,
        boundary_overrides=load_boundary_overrides(getattr(args, "boundaries", None)),
    )
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

    _emit_progress(8, "正在解析 PDF", "读取页面结构并识别题目边界")
    result = scan_pdf(
        pdf_path,
        output_dir=workdir,
        render=True,
        dpi=args.dpi,
        boundary_overrides=load_boundary_overrides(getattr(args, "boundaries", None)),
    )
    if getattr(args, "title", None):
        result.name = args.title
    _emit_progress(
        52,
        "题目识别完成",
        f"识别到 {len(result.questions)} 道题，正在整理切题结果",
    )
    manifest_path = workdir / "manifest.json"
    save_scan_result(result, manifest_path)

    _emit_progress(60, "正在生成 PPT", f"试卷标题：{result.name}")
    pptx_path = workdir / f"{pdf_path.stem}_讲题版.pptx"
    qa_path = workdir / "qa.json"
    report = build_ppt(
        manifest_path=manifest_path,
        output_pptx=pptx_path,
        qa_json=qa_path,
    )
    _emit_progress(
        78,
        "PPT 排版完成",
        f"已生成 {report['slide_count']} 页，正在生成放映预览",
    )
    preview_dir = workdir / "preview"
    preview_files = render_slide_previews(
        manifest_path=manifest_path,
        qa_json=qa_path,
        output_dir=preview_dir,
    )

    _emit_progress(96, "正在完成检查", "预览已生成，正在汇总 QA 结果")
    combined_status = (
        "PASS"
        if result.status == "PASS" and report["status"] == "PASS"
        else "MANUAL_REQUIRED"
    )
    summary = {
        "status": combined_status,
        "scan_status": result.status,
        "layout_status": report["status"],
        "title": result.name,
        "question_count": len(result.questions),
        "cross_page_questions": [q.number for q in result.questions if q.cross_page],
        "pptx": str(report["output"]),
        "manifest": str(manifest_path),
        "qa": str(qa_path),
        "preview_dir": str(preview_dir),
        "preview_files": preview_files,
        "slides": report["slides"],
        "warnings": result.warnings,
        "violations": report["violations"],
    }
    _emit_progress(
        100,
        "生成完成",
        f"{len(result.questions)} 道题 · {report['slide_count']} 页 PPT",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if combined_status == "PASS" else 3


def main() -> int:
    _configure_utf8_stdio()
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
    scan.add_argument("--boundaries", help="人工题目起始边界 JSON 文件")

    build = sub.add_parser("build", help="自动切题并生成课堂讲评 PPT")
    build.add_argument("pdf")
    build.add_argument("--out-dir")
    build.add_argument("--dpi", type=int, default=180)
    build.add_argument("--title", help="覆盖PPT页眉中的试卷名称")
    build.add_argument("--boundaries", help="人工题目起始边界 JSON 文件")

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
