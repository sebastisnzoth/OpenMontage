# OpenMontage Music Video Studio

MVP web para crear un videoclip a partir de una canción y una foto o video.

## Qué hace ahora

- Sube una canción (MP3, WAV, M4A u otro formato soportado por FFmpeg).
- Sube una foto o un video del artista.
- Genera un MP4 sincronizado con la duración de la canción.
- Modos 16:9 cinematográfico, 16:9 limpio y vertical 9:16.
- En foto aplica un movimiento suave tipo Ken Burns en modo cinematográfico.
- En video repite el material visual si es más corto que la canción.
- Guarda cada proyecto en `music_video_projects/<id>/`.
- Expone estado y descarga por API.

## Ejecutar

Desde la raíz de OpenMontage:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg
uvicorn music_video_web.app:app --host 0.0.0.0 --port 8080 --reload
```

Abrir:

```text
http://localhost:8080
```

## API

- `GET /` interfaz web
- `POST /api/projects` crea y renderiza un proyecto
- `GET /api/projects/{id}` devuelve estado/metadata
- `GET /api/projects/{id}/download` descarga el MP4

## Próximas etapas

La intención es usar este frontend como puerta de entrada a los pipelines de OpenMontage:

1. análisis de letra y estructura musical;
2. detección de versos, estribillos, puentes y cambios de energía;
3. storyboard automático por escenas;
4. generación image-to-video / text-to-video mediante providers de OpenMontage;
5. consistencia de identidad a partir de la foto del artista;
6. lip-sync en planos cantados;
7. montaje al beat y transiciones;
8. revisión en Backlot antes del render final;
9. creación automática de Shorts/Reels/TikTok.

El MVP actual no necesita una API de IA para producir el primer video: solo Python + FFmpeg. Los providers de IA se conectarán como una segunda capa, sin cambiar el flujo de carga para el usuario.
