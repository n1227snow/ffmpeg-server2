import os
import uuid
import shutil
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="FFmpeg REST API")

JOBS = {}  # in-memory job store


def resolve_command(command: str, input_paths: list[str], output_path: str) -> str:
    # Replace {input0}, {input1}, etc.
    for i, path in enumerate(input_paths):
        command = command.replace(f"{{input{i}}}", path)
    # {input} alone maps to first file
    command = command.replace("{input}", input_paths[0] if input_paths else "")
    command = command.replace("{output}", output_path)
    return command


async def run_job(job_id: str, input_paths: list[str], full_command: str, output_path: str, workdir: str):
    JOBS[job_id]["status"] = "PROCESSING"
    try:
        cmd = resolve_command(full_command, input_paths, output_path)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workdir
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            JOBS[job_id]["status"] = "FAILED"
            JOBS[job_id]["error"] = stderr.decode()[-1000:]
        else:
            JOBS[job_id]["status"] = "FINISHED"
            JOBS[job_id]["output_path"] = output_path
    except Exception as e:
        JOBS[job_id]["status"] = "FAILED"
        JOBS[job_id]["error"] = str(e)


@app.post("/api/ffmpeg/jobs/upload")
async def upload_job(
    full_command: str = Form(...),
    output_extension: str = Form(...),
    file: Optional[UploadFile] = File(None),
    file1: Optional[UploadFile] = File(None),
    file2: Optional[UploadFile] = File(None),
    file3: Optional[UploadFile] = File(None),
    file4: Optional[UploadFile] = File(None),
    file5: Optional[UploadFile] = File(None),
    file6: Optional[UploadFile] = File(None),
    file7: Optional[UploadFile] = File(None),
):
    job_id = str(uuid.uuid4())
    workdir = tempfile.mkdtemp(prefix=f"ffmpeg_{job_id}_")

    # Save all uploaded files in order
    uploaded = [f for f in [file, file1, file2, file3, file4, file5, file6, file7] if f is not None]
    input_paths = []

    for i, upload in enumerate(uploaded):
        ext = Path(upload.filename).suffix if upload.filename else f".bin"
        dest = os.path.join(workdir, f"input{i}{ext}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        input_paths.append(dest)

    output_path = os.path.join(workdir, f"output.{output_extension}")

    JOBS[job_id] = {
        "status": "PENDING",
        "output_path": None,
        "error": None,
        "workdir": workdir,
    }

    # Run ffmpeg in background
    asyncio.create_task(run_job(job_id, input_paths, full_command, output_path, workdir))

    return JSONResponse({"success": True, "job_id": job_id, "status": "PENDING"}, status_code=202)


@app.get("/api/ffmpeg/jobs/{job_id}")
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job["status"], "error": job.get("error")}


@app.get("/api/ffmpeg/jobs/{job_id}/download")
async def download_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "FINISHED":
        raise HTTPException(status_code=400, detail=f"Job not finished, status: {job['status']}")

    output_path = job["output_path"]
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(output_path, filename=Path(output_path).name)


@app.get("/health")
async def health():
    return {"status": "ok"}
