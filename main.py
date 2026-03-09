import os
import uuid
import shutil
import asyncio
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="FFmpeg REST API")

JOBS = {}

API_KEY = os.environ.get("API_KEY", "changeme")


def check_auth(authorization: Optional[str] = None):
    if not authorization or authorization != f"Apikey {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def save_input(value, index: int, workdir: str) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        ext = Path(value.split("?")[0]).suffix or ".bin"
        dest = os.path.join(workdir, f"input{index}{ext}")
        req = urllib.request.Request(value, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(dest, "wb") as f:
            shutil.copyfileobj(response, f)
        return dest
    if hasattr(value, "file"):
        ext = Path(value.filename).suffix if value.filename else ".bin"
        dest = os.path.join(workdir, f"input{index}{ext}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(value.file, f)
        return dest
    return None


def resolve_placeholders(text: str, input_paths: list, output_path: str) -> str:
    for i, path in enumerate(input_paths):
        text = text.replace(f"{{input{i}}}", path)
    text = text.replace("{input}", input_paths[0] if input_paths else "")
    text = text.replace("{output}", output_path)
    return text


async def run_job(job_id: str, input_paths: list, full_command: str, output_path: str, workdir: str):
    JOBS[job_id]["status"] = "PROCESSING"
    try:
        # Resolve placeholders inside any text/script files (e.g. filter_complex_script)
        for path in input_paths:
            try:
                with open(path, "r") as f:
                    content = f.read()
                resolved = resolve_placeholders(content, input_paths, output_path)
                if resolved != content:
                    with open(path, "w") as f:
                        f.write(resolved)
            except (UnicodeDecodeError, IsADirectoryError):
                pass  # skip binary files

        cmd = resolve_placeholders(full_command, input_paths, output_path)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workdir
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            JOBS[job_id]["status"] = "FAILED"
            JOBS[job_id]["error"] = stderr.decode()[-2000:]
        else:
            JOBS[job_id]["status"] = "FINISHED"
            JOBS[job_id]["output_path"] = output_path
    except Exception as e:
        JOBS[job_id]["status"] = "FAILED"
        JOBS[job_id]["error"] = str(e)


@app.post("/api/ffmpeg/jobs/upload")
async def upload_job(
    authorization: Optional[str] = Header(None),
    full_command: str = Form(...),
    output_extension: str = Form(...),
    file: Optional[str] = Form(None),
    file1: Optional[UploadFile] = File(None),
    file2: Optional[str] = Form(None),
    file3: Optional[str] = Form(None),
    file4: Optional[UploadFile] = File(None),
    file5: Optional[UploadFile] = File(None),
    file6: Optional[UploadFile] = File(None),
    file7: Optional[UploadFile] = File(None),
):
    check_auth(authorization)
    job_id = str(uuid.uuid4())
    workdir = tempfile.mkdtemp(prefix=f"ffmpeg_{job_id}_")

    raw_inputs = [file, file1, file2, file3, file4, file5, file6, file7]
    input_paths = []

    for i, val in enumerate(raw_inputs):
        if val is None:
            continue
        path = save_input(val, i, workdir)
        if path:
            input_paths.append(path)

    output_path = os.path.join(workdir, f"output.{output_extension}")

    JOBS[job_id] = {
        "status": "PENDING",
        "output_path": None,
        "error": None,
        "workdir": workdir,
    }

    asyncio.create_task(run_job(job_id, input_paths, full_command, output_path, workdir))

    return JSONResponse({"success": True, "job_id": job_id, "status": "PENDING"}, status_code=202)


@app.get("/api/ffmpeg/jobs/{job_id}")
async def get_job(job_id: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job["status"], "error": job.get("error")}


@app.get("/api/ffmpeg/jobs/{job_id}/download")
async def download_job(job_id: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
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
