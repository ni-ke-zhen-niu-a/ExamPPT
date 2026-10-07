from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("EXAMPPT_SERVER_DATA", ROOT / ".server-data"))
MAX_UPLOAD_BYTES = int(os.environ.get("EXAMPPT_MAX_UPLOAD_BYTES", 30 * 1024 * 1024))
PROGRESS_PREFIX = "EXAMPPT_PROGRESS:"

DATA_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass
class Job:
    id: str
    status: str = "queued"
    percent: int = 0
    stage: str = "等待处理"
    detail: str = ""
    title: str = ""
    pptx: str = ""
    error: str = ""
    question_count: int = 0
    slide_count: int = 0
    output_dir: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def public(self) -> dict[str, Any]:
        with self.lock:
            data = {
                "id": self.id,
                "status": self.status,
                "percent": self.percent,
                "stage": self.stage,
                "detail": self.detail,
                "title": self.title,
                "pptx": self.pptx,
                "error": self.error,
                "question_count": self.question_count,
                "slide_count": self.slide_count,
                "output_dir": self.output_dir,
            }
        data["download_ready"] = bool(data["pptx"]) and Path(data["pptx"]).exists()
        return data


jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()

app = FastAPI(
    title="ExamPPT Server",
    version="0.1.0",
    description="PDF 试卷转讲题 PPT 的任务服务",
)


def _set_job(job: Job, **changes: Any) -> None:
    with job.lock:
        for key, value in changes.items():
            setattr(job, key, value)


def _run_job(job: Job, pdf_path: Path, out_dir: Path) -> None:
    _set_job(job, status="running", percent=2, stage="正在启动转换引擎", output_dir=str(out_dir))

    python_exe = getattr(sys, "_base_executable", sys.executable)
    command = [
        python_exe,
        "-m",
        "examppt.cli",
        "build",
        str(pdf_path),
        "--out-dir",
        str(out_dir),
    ]

    env = os.environ.copy()
    python_paths = [str(ROOT / "src")]
    if sys.prefix != sys.base_prefix:
        python_paths.append(str(Path(sys.prefix) / "Lib" / "site-packages"))
    inherited = env.get("PYTHONPATH", "")
    if inherited:
        python_paths.append(inherited)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)

    result_file = out_dir / "core-result.json"
    stderr_lines: list[str] = []

    try:
        with result_file.open("w", encoding="utf-8", newline="") as stdout_file:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                env=env,
                stdout=stdout_file,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )

            def read_progress() -> None:
                try:
                    assert process.stderr is not None
                    for raw_line in process.stderr:
                        line = raw_line.strip()
                        if not line:
                            continue
                        if line.startswith(PROGRESS_PREFIX):
                            try:
                                payload = json.loads(line[len(PROGRESS_PREFIX) :])
                                _set_job(
                                    job,
                                    percent=int(payload.get("percent", job.percent)),
                                    stage=str(payload.get("stage", job.stage)),
                                    detail=str(payload.get("detail", "")),
                                )
                            except Exception:
                                stderr_lines.append(line)
                        else:
                            stderr_lines.append(line)
                except (OSError, ValueError):
                    pass

            progress_thread = threading.Thread(
                target=read_progress,
                daemon=True,
                name=f"examppt-progress-{job.id[:8]}",
            )
            progress_thread.start()

            return_code = process.wait()
            stdout_file.flush()

            if process.stderr is not None:
                try:
                    process.stderr.close()
                except OSError:
                    pass
            progress_thread.join(timeout=1.0)

        stdout = result_file.read_text(encoding="utf-8").strip()
        if not stdout:
            raise RuntimeError("\n".join(stderr_lines) or f"ExamPPT Core exited with code {return_code}")

        result = json.loads(stdout)
        pptx = Path(result["pptx"])

        if return_code not in (0, 3):
            raise RuntimeError("\n".join(stderr_lines) or f"ExamPPT Core exited with code {return_code}")
        if not pptx.exists():
            raise RuntimeError("生成完成，但未找到输出 PPT 文件。")

        _set_job(
            job,
            status="completed" if result.get("status") == "PASS" else "needs_review",
            percent=100,
            stage="生成完成",
            detail="",
            title=str(result.get("title") or ""),
            pptx=str(pptx),
            question_count=int(result.get("question_count", 0)),
            slide_count=len(result.get("slides", [])),
        )
    except Exception as exc:
        _set_job(job, status="failed", stage="生成失败", error=str(exc))


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    original_name: str = Form(""),
) -> dict[str, Any]:
    filename = Path(original_name or file.filename or "exam.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="当前仅支持 PDF 文件。")

    job_id = uuid.uuid4().hex
    job_dir = DATA_ROOT / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = input_dir / filename

    total = 0
    try:
        with pdf_path.open("wb") as target:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="PDF 文件过大。")
                target.write(chunk)
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    finally:
        await file.close()

    job = Job(id=job_id, output_dir=str(output_dir))
    with jobs_lock:
        jobs[job_id] = job

    thread = threading.Thread(
        target=_run_job,
        args=(job, pdf_path, output_dir),
        daemon=True,
        name=f"examppt-job-{job_id[:8]}",
    )
    thread.start()

    return job.public()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return job.public()


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在。")

    data = job.public()
    if not data["download_ready"]:
        raise HTTPException(status_code=409, detail="PPT 尚未生成完成。")

    pptx = Path(data["pptx"])
    return FileResponse(
        path=pptx,
        filename=pptx.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
