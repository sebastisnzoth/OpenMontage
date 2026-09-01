from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent
WORK_ROOT = PROJECT_ROOT / "music_video_projects"
WORK_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="OpenMontage Music Video Studio", version="0.1.0")


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffmpeg command failed")


def _duration(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffprobe failed")
    return float(proc.stdout.strip())


def _safe_suffix(filename: Optional[str], fallback: str) -> str:
    if not filename:
        return fallback
    suffix = Path(filename).suffix.lower()
    return suffix if suffix and len(suffix) <= 10 else fallback


def _render_photo(photo: Path, audio: Path, output: Path, style: str) -> None:
    duration = _duration(audio)
    if style == "cinematic":
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
            "zoompan=z='min(zoom+0.0007,1.12)':d=125:s=1920x1080:fps=25,"
            "format=yuv420p"
        )
    elif style == "vertical":
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            "zoompan=z='min(zoom+0.0007,1.10)':d=125:s=1080x1920:fps=25,"
            "format=yuv420p"
        )
    else:
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
        )

    _run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(photo),
            "-i",
            str(audio),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output),
        ]
    )


def _render_video(video: Path, audio: Path, output: Path, style: str) -> None:
    duration = _duration(audio)
    if style == "vertical":
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p"
    else:
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p"

    _run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output),
        ]
    )


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>OpenMontage Music Video Studio</title>
<style>
:root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
body { margin:0; min-height:100vh; background:radial-gradient(circle at top,#22234b 0,#0c0d16 46%,#080910 100%); color:#f6f7fb; }
.wrap { max-width:900px; margin:auto; padding:56px 22px; }
.card { background:rgba(18,19,32,.88); border:1px solid #343654; border-radius:24px; padding:28px; box-shadow:0 24px 80px rgba(0,0,0,.38); }
h1 { font-size:clamp(34px,6vw,62px); margin:0 0 8px; letter-spacing:-.04em; }
.sub { color:#afb3ca; font-size:18px; margin:0 0 30px; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
label { display:block; font-weight:700; margin:0 0 8px; }
input, select, textarea { width:100%; box-sizing:border-box; border:1px solid #3b3e5d; background:#11131f; color:#fff; border-radius:14px; padding:13px; }
textarea { min-height:120px; resize:vertical; }
.full { grid-column:1/-1; }
button { border:0; border-radius:14px; padding:15px 22px; font-weight:800; font-size:16px; background:linear-gradient(135deg,#8d69ff,#ff4d9d); color:white; cursor:pointer; }
small { color:#8f94aa; }
#status { margin-top:18px; white-space:pre-wrap; color:#dfe1f1; }
@media(max-width:700px){.grid{grid-template-columns:1fr}.full{grid-column:auto}}
</style>
</head>
<body>
<div class="wrap">
  <h1>Music Video Studio</h1>
  <p class="sub">Subí tu canción y una foto o video. OpenMontage crea un primer videoclip listo para revisar.</p>
  <div class="card">
    <form id="form" class="grid">
      <div>
        <label>Canción</label>
        <input name="song" type="file" accept="audio/*" required />
      </div>
      <div>
        <label>Foto o video</label>
        <input name="visual" type="file" accept="image/*,video/*" required />
      </div>
      <div>
        <label>Formato / estilo</label>
        <select name="style">
          <option value="cinematic">Cinemático 16:9</option>
          <option value="clean">Limpio 16:9</option>
          <option value="vertical">Vertical 9:16</option>
        </select>
      </div>
      <div>
        <label>Nombre del proyecto</label>
        <input name="title" placeholder="Mi videoclip" />
      </div>
      <div class="full">
        <label>Letra (opcional)</label>
        <textarea name="lyrics" placeholder="Pegá la letra para la próxima etapa de storyboard y lip-sync..."></textarea>
      </div>
      <div class="full">
        <button type="submit">Generar videoclip</button>
        <small>Necesita FFmpeg instalado. El MVP renderiza localmente; la generación IA por escenas se conecta después mediante providers.</small>
        <div id="status"></div>
      </div>
    </form>
  </div>
</div>
<script>
const form = document.querySelector('#form');
const statusBox = document.querySelector('#status');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  statusBox.textContent = 'Procesando...';
  const data = new FormData(form);
  try {
    const r = await fetch('/api/projects', {method:'POST', body:data});
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || 'Error');
    statusBox.innerHTML = `Listo: ${j.title}\n<a style="color:#bca8ff" href="${j.download_url}">Descargar videoclip MP4</a>`;
  } catch (err) {
    statusBox.textContent = 'Error: ' + err.message;
  }
});
</script>
</body>
</html>"""


@app.post("/api/projects")
async def create_project(
    song: UploadFile = File(...),
    visual: UploadFile = File(...),
    title: str = Form("Mi videoclip"),
    style: str = Form("cinematic"),
    lyrics: str = Form(""),
):
    if style not in {"cinematic", "clean", "vertical"}:
        raise HTTPException(status_code=400, detail="Estilo inválido")
    if not song.content_type or not song.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="El primer archivo debe ser audio")
    if not visual.content_type or not (
        visual.content_type.startswith("image/") or visual.content_type.startswith("video/")
    ):
        raise HTTPException(status_code=400, detail="El visual debe ser una imagen o un video")

    project_id = uuid.uuid4().hex[:12]
    project_dir = WORK_ROOT / project_id
    project_dir.mkdir(parents=True)

    song_path = project_dir / f"song{_safe_suffix(song.filename, '.mp3')}"
    visual_path = project_dir / f"visual{_safe_suffix(visual.filename, '.jpg')}"
    output_path = project_dir / "music-video.mp4"

    with song_path.open("wb") as f:
        shutil.copyfileobj(song.file, f)
    with visual_path.open("wb") as f:
        shutil.copyfileobj(visual.file, f)

    metadata = {
        "id": project_id,
        "title": title.strip() or "Mi videoclip",
        "style": style,
        "lyrics": lyrics,
        "song": song_path.name,
        "visual": visual_path.name,
        "status": "rendering",
    }
    (project_dir / "project.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        if visual.content_type.startswith("image/"):
            _render_photo(visual_path, song_path, output_path, style)
        else:
            _render_video(visual_path, song_path, output_path, style)
    except Exception as exc:
        metadata["status"] = "failed"
        metadata["error"] = str(exc)
        (project_dir / "project.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        raise HTTPException(status_code=500, detail=f"No se pudo renderizar: {exc}") from exc

    metadata["status"] = "complete"
    metadata["output"] = output_path.name
    (project_dir / "project.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return JSONResponse(
        {
            "id": project_id,
            "title": metadata["title"],
            "status": "complete",
            "download_url": f"/api/projects/{project_id}/download",
        }
    )


@app.get("/api/projects/{project_id}")
def project_status(project_id: str):
    project_dir = WORK_ROOT / project_id
    metadata_path = project_dir / "project.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


@app.get("/api/projects/{project_id}/download")
def download_project(project_id: str):
    output = WORK_ROOT / project_id / "music-video.mp4"
    if not output.exists():
        raise HTTPException(status_code=404, detail="El video todavía no está disponible")
    return FileResponse(output, media_type="video/mp4", filename=f"{project_id}-music-video.mp4")
