# Container Setup Guide

This project supports both VS Code Dev Containers for day-to-day development and a slimmer runtime image for headless execution. Follow the workflow that fits your use case.

## 1. Prerequisites

- Docker Desktop 4.20+ (or another engine compatible with Docker Compose v2)
- VS Code with the **Dev Containers** extension (`ms-vscode-remote.remote-containers`) if you plan to develop inside the container
- Optional: GitHub Codespaces if you prefer a hosted development environment

## 2. Develop Inside a Dev Container (Option A)

1. Install the prerequisites above.
2. Open VS Code, press `F1` / `Ctrl+Shift+P`, and run `Dev Containers: Rebuild and Reopen in Container`.
3. VS Code builds the image defined in `.devcontainer/Dockerfile` and then runs `scripts/bootstrap_devcontainer.sh`, which upgrades `pip`, installs every `requirements*.txt`, and performs a lightweight `pip check` to confirm dependencies.
4. Once the container is ready, open a terminal inside VS Code and run `python -m pytest -q` to ensure the environment works as expected.
5. Host directories `data/`, `models/`, and `reports/` are bind-mounted into the container. Comment any mount in `.devcontainer/devcontainer.json` if you do not need that folder inside the container.

### Environment Variables

- Copy `.env.example` to `.env` on the host before reopening in the container so API keys are available.
- VS Code reuses your `.env` via the bind mount; for sensitive keys consider using VS Code secret storage.

### Useful Commands Inside the Dev Container

```bash
# Phase 2 Lite smoke test
python phase2_lite.py

# Generate a report
python generate_fast_reports.py generate 1 matches for la-liga

# Run test suite
python -m pytest -q

# Lint
ruff check .
```

## 3. Build and Run the Runtime Image

The root-level `Dockerfile` creates a lean Python 3.11 image that includes only the dependencies required to execute the prediction engine or report generators.

```bash
# Build the runtime image
docker build -t sports-prediction-runtime .

# Execute the harness with local data mounts
docker run --rm \
  --env-file .env \
  -v "${PWD}/data:/app/data" \
  -v "${PWD}/models:/app/models" \
  -v "${PWD}/reports:/app/reports" \
  sports-prediction-runtime python phase2_lite.py
```

### What is the runtime image?

The runtime image is a pre-built snapshot of the project plus all Python dependencies packaged for execution. Unlike the dev container (which also carries IDE tooling), the runtime image focuses on running commands such as `python phase2_lite.py` or `python generate_fast_reports.py` deterministically—ideal for cron jobs, automation, or quick headless runs.

## 4. Docker Compose Workflow

`docker-compose.yml` mirrors the runtime image but mounts host directories automatically.

```bash
# Build the service (first time or when dependencies change)
docker compose build

# Run Phase 2 Lite
docker compose run --rm phase2-lite

# Generate reports from the same container baseline
docker compose run --rm phase2-lite python generate_fast_reports.py generate 1 matches for la-liga
```

To clean up containers and volumes:

```bash
docker compose down --volumes --remove-orphans
```

## 5. Troubleshooting

| Issue | Resolution |
| --- | --- |
| Container build is slow | Ensure Docker BuildKit is enabled and that `.dockerignore` excludes large folders (`data/`, `models/`, etc.). |
| `ModuleNotFoundError` for native libs | Confirm the apt packages in `.devcontainer/Dockerfile` include the required system library. |
| API keys missing inside container | Check that `.env` exists before building/running or pass `--env-file .env`. |
| Permission errors on bind mounts (Windows) | Keep the repo outside protected folders (e.g., avoid Documents) and verify Docker Desktop file sharing permissions. |

The container setup is now ready for local development, reproducible testing, and transfer to other machines. If you need automation helpers (Makefile, VS Code tasks, CI workflows), let me know and I can add them.
