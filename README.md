# FFmpeg REST API

A simple self-hosted FFmpeg API with no command restrictions.

## Endpoints

### Submit a job
`POST /api/ffmpeg/jobs/upload`

Multipart form fields:
- `file` — first input file (maps to `{input0}`)
- `file1` — second input file (maps to `{input1}`)
- `file2`, `file3`, `file4`, `file5` — additional inputs
- `full_command` — ffmpeg command using `{input0}`, `{input1}`, `{output}` placeholders
- `output_extension` — e.g. `mp4`, `mp3`

### Check status
`GET /api/ffmpeg/jobs/{job_id}`

Statuses: `PENDING`, `PROCESSING`, `FINISHED`, `FAILED`

### Download result
`GET /api/ffmpeg/jobs/{job_id}/download`

## Deploy to Railway

1. Push this repo to GitHub
2. Go to railway.app → New Project → Deploy from GitHub
3. Railway auto-detects the Dockerfile and deploys
4. Use the generated URL in your n8n workflow

## n8n HTTP Request4 URL changes

| Old (upload-post.com) | New (your Railway URL) |
|---|---|
| `POST .../ffmpeg/jobs/upload` | `POST https://YOUR-APP.up.railway.app/api/ffmpeg/jobs/upload` |
| `GET .../ffmpeg/jobs/{job_id}` | `GET https://YOUR-APP.up.railway.app/api/ffmpeg/jobs/{job_id}` |
| `GET .../ffmpeg/jobs/{job_id}/download` | `GET https://YOUR-APP.up.railway.app/api/ffmpeg/jobs/{job_id}/download` |
