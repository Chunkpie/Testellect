# 14 — Docker Deployment

## Container topology

Per `02-system-architecture.md`, six logical pieces, mapped to Docker Compose services:

```yaml
# docker-compose.yml (conceptual structure — fill in exact build context/env per actual repo layout)
services:
  frontend:
    build: ./docker/frontend
    ports: ["443:443", "80:80"]   # Nginx serving built React app + reverse-proxying /api to backend
    depends_on: [backend]

  backend:
    build: ./docker/backend
    ports: ["8000:8000"]
    volumes:
      - db_data:/data/db
      - storage_data:/data/storage
      - backup_data:/data/backups
    environment:
      - DATABASE_URL=sqlite:////data/db/gseb.db
      - OLLAMA_BASE_URL=http://ollama:11434
      - CHROMA_BASE_URL=http://chromadb:8001
      - FILE_STORAGE_PATH=/data/storage
      - BACKUP_PATH=/data/backups
    depends_on: [ollama, chromadb]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_models:/root/.ollama
    ports: ["11434:11434"]
    # GPU passthrough optional — see "Model Provisioning" below for CPU-only fallback

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    ports: ["8001:8000"]

volumes:
  db_data:
  storage_data:
  backup_data:
  ollama_models:
  chroma_data:
```

One command deployment: `docker compose up --build`, matching the project summary's stated requirement exactly.

## Model Provisioning

Ollama doesn't ship with Qwen3 8B pre-pulled — the model must be pulled on first run. Two approaches, document both in `16-installation.md`:

1. **Online provisioning (one-time, before going fully offline)**: run `docker compose exec ollama ollama pull qwen3:8b` (and the chosen embedding model, per `07-rag-architecture.md`) once, while the deployment machine still has internet access (e.g., during initial school setup). After this, the system runs fully offline for all subsequent operation — this is consistent with "fully offline" meaning *no internet required to operate*, not literally no internet ever in the model's history.
2. **Offline provisioning (no internet ever available)**: provide a `scripts/load_models_offline.sh` that loads pre-downloaded model blob files (distributed via USB drive or local network transfer from a machine that does have internet) directly into the `ollama_models` volume's expected directory structure, for schools with zero internet access even during setup.

A first-run setup wizard or script (`scripts/first_run_check.sh`) should verify the required models are present via `ollama list` before allowing the rest of the app to be marked "ready," and the frontend should show a clear "AI models not yet installed" state rather than cryptic timeouts if a teacher tries to upload a book before models are provisioned.

## GPU vs CPU-only deployment

- If the host has an NVIDIA GPU (e.g., the RTX 3050 reference hardware in `01-project-overview.md`) and `nvidia-container-toolkit` is installed, add the standard `deploy.resources.reservations.devices` GPU passthrough block to the `ollama` service for faster inference.
- If no GPU is available or toolkit isn't installed, Ollama falls back to CPU automatically — no compose changes required, just slower generation (set expectations per `06-ai-engine.md` → "Degrading gracefully on weak hardware").
- Document both paths explicitly in `16-installation.md` with a simple "do you have an NVIDIA GPU? yes/no" branch, since most school IT staff won't know how to diagnose this themselves.

## Networking

- Internal service-to-service traffic (backend→ollama, backend→chromadb) stays on the Docker Compose internal network — only `frontend` (443/80) needs to be exposed to the school LAN. Avoid exposing `ollama`'s and `chromadb`'s ports to the host/LAN in production compose files (only expose them in a dev override file) since they have no authentication of their own.
- Provide a `docker-compose.override.yml` for local development that does expose 11434/8001 directly, for easier debugging, kept separate from the production compose file per `17-developer-guide.md`.

## TLS

Per `12-security.md`, serve over HTTPS even on LAN. The `frontend` Nginx container should be configured with a certificate — for v1, a self-signed cert generated during setup (`scripts/generate_cert.sh`) is acceptable, with the installation guide explaining how staff/teacher devices can trust it (or simply accept the browser warning once, documented clearly rather than silently expected).

## Volumes and data persistence

| Volume | Contents | Backup-critical? |
|---|---|---|
| `db_data` | SQLite database file | Yes — primary |
| `storage_data` | Uploaded PDFs, generated papers, OMR sheets/scans, reports | Yes |
| `backup_data` | Generated backup archives | Should itself be copied off-machine periodically (school's responsibility, documented) |
| `ollama_models` | Pulled model weights | No — re-provisionable, large, exclude from routine backups |
| `chroma_data` | Vector embeddings | Technically re-derivable by reprocessing books, but back up anyway since reprocessing is slow — treat as semi-critical |

## Updating the application

- New version rollout: `git pull` (or unpack a new release bundle) → `docker compose build` → run Alembic migrations (`docker compose exec backend alembic upgrade head`) → `docker compose up -d`.
- Always back up before upgrading (`scripts/backup.sh` calling the same logic as the `/backup` API endpoint) — document this as a mandatory pre-upgrade step in `17-developer-guide.md`/`16-installation.md`, not optional.

## Resource limits

On shared/modest hardware, consider setting `mem_limit`/`cpus` constraints on the `ollama` service in production compose so a large generation batch can't starve the `backend`/`frontend` containers entirely — tune actual values against real observed usage during Phase 8 hardening (`19-roadmap.md`), don't guess fixed numbers prematurely.
