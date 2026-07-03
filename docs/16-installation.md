# 16 — Installation Guide (End User / School IT Staff)

This document is written for the person setting up the platform at a school — typically an administrator or IT-comfortable teacher, not necessarily a developer. Keep this in sync with actual `docker compose` behavior as the system is built; if a step here doesn't match reality, fix this doc, don't leave it stale.

## What you need before starting

- A PC or laptop dedicated to running the platform (the rest of the school accesses it over the local network/Wi-Fi). Reference hardware: 16GB+ RAM recommended (24GB tested), a discrete GPU is optional but speeds up AI features significantly.
- [Docker Desktop](https://www.docker.com/) (Windows/Mac) or Docker Engine + Docker Compose (Linux) installed on that PC.
- Internet access **for initial setup only** (to download the application and pull AI models). After setup, internet is not required for daily use.
- Roughly 15–20GB of free disk space (application + AI models + growing data over time).

## Step 1 — Get the application files

Download/copy the application folder onto the host PC (via USB drive, local network transfer, or `git clone` if internet is available on this machine). You should end up with a folder containing `docker-compose.yml` and the `backend/`, `frontend/`, `docker/` subfolders.

## Step 2 — First-time configuration

1. Copy `.env.example` to `.env` in the project root.
2. Run the provided setup script (`scripts/generate_secrets.sh` or equivalent) to generate a secure `JWT_SECRET_KEY` and populate it into `.env` automatically — do not type in a secret manually or leave the example value in place.
3. Decide: does this PC have an NVIDIA GPU?
   - **Yes** → ensure `nvidia-container-toolkit` is installed (see Docker's official GPU setup guide for your OS), and use the default `docker-compose.yml` as-is.
   - **No** → no changes needed; Ollama will run on CPU automatically (AI features will be slower but functional).

## Step 3 — Start the application

```bash
docker compose up --build
```

First start will take several minutes (building containers, pulling base images). Leave it running until you see the backend's health check pass (logs will show the backend reporting "ready").

## Step 4 — Provision AI models (one-time, requires internet)

In a new terminal, with the containers still running:

```bash
docker compose exec ollama ollama pull qwen3:8b
docker compose exec ollama ollama pull <embedding-model-name>
```

(See `14-docker-deployment.md` → "Model Provisioning" for the offline alternative if this machine never has internet access.)

This step downloads several gigabytes — expect it to take a while depending on connection speed. Once complete, the AI features (question generation, knowledge base processing, AI assistant) are usable without internet from then on.

## Step 5 — Access the application

Open a browser on the host PC (or any device on the same school network) and navigate to:

```
https://<host-pc-local-ip>
```

You'll likely see a browser warning about the self-signed certificate (per `12-security.md`/`14-docker-deployment.md`) — this is expected for a LAN-only deployment; choose "proceed anyway" / "accept the risk" depending on your browser. To find the host PC's local IP, run `ipconfig` (Windows) or `ip addr` (Linux/Mac) on the host machine.

## Step 6 — Create the first administrator account

On first run, the system should prompt for initial admin setup (school name, admin email/password) directly in the UI — there is no separate manual database step required. From there, the administrator logs in and:

1. Confirms/edits the school profile (Settings → School Profile).
2. Creates teacher and principal accounts (Settings → Users).
3. Creates classes (Settings or Classes module).
4. Bulk-imports or manually adds students per class.

Teachers can then begin uploading textbook PDFs (Books module) once accounts exist.

## Connecting other devices

Any device (teacher laptop, staff PC) on the same local network/Wi-Fi can access the platform at the same `https://<host-pc-local-ip>` address — no separate installation needed on those devices, only a modern web browser. Make sure the host PC stays powered on and connected to the network during school hours for others to access it.

## Backups

Set up a recurring habit (weekly is a reasonable minimum) of:

1. Running a backup from Settings → Backups (Administrator), or via `scripts/backup.sh` on the host PC.
2. Copying the resulting backup file off the host PC — to a USB drive, a network share, or another machine — since a backup that lives only on the same machine doesn't protect against that machine failing.

## Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser can't reach the site at all | Containers not running, or wrong IP | Check `docker compose ps`, confirm host IP |
| "AI models not yet installed" message | Step 4 skipped or failed | Re-run the `ollama pull` commands, check internet connectivity at that time |
| Book upload stuck "processing" for a very long time | Slow hardware (CPU-only inference), or Ollama unreachable | Check `docker compose logs ollama`/`backend`; on CPU-only hardware, large books legitimately take longer — see `06-ai-engine.md` |
| Forgot administrator password | — | Use the password reset flow if implemented, or contact whoever set up the deployment to reset via a documented admin-recovery script |
| OMR scan results look wrong/garbled | Poor scan quality (lighting, angle, torn corner markers) | Rescan following the photo-quality tips in the OMR module's in-app help; see `09-omr-engine.md` test cases for what conditions are/aren't supported |

## Updating to a new version

See `14-docker-deployment.md` → "Updating the application" — always back up first.
