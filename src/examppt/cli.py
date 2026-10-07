from __future__ import annotations
import argparse
import os
import platform
import sys
from . import __version__

def doctor() -> int:
    print(f"ExamPPT {__version__}")
    print(f"Python: {platform.python_version()}")
    print(f"System: {platform.system()} {platform.release()} {platform.machine()}")
    if os.name != "nt":
        print("Status: V0.1 targets Windows 10/11 x64.")
        return 1
    print("PPTX generation: available (Office/WPS not required for generation)")
    print("PowerPoint/WPS playback QA: adapter under development")
    return 0

def main() -> int:
    p = argparse.ArgumentParser(prog="exam-ppt", description="PDF试卷无损转PPT 工具")
    p.add_argument("--version", action="version", version=f"ExamPPT {__version__}")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("doctor", help="检查本机运行环境")
    build = sub.add_parser("build", help="生成课堂讲评PPT（开发中）")
    build.add_argument("pdf")
    args = p.parse_args()
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "build":
        print("build command is not public-ready yet; use the GUI/CLI release when V0.1 is published.", file=sys.stderr)
        return 2
    p.print_help()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
