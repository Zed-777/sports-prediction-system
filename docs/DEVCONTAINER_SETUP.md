# Devcontainer & Docker Quick Start

This project includes both a VS Code Dev Container configuration (`.devcontainer/`) and a `docker-compose.yml` for running the Phase 2 Lite service locally.

Two common workflows:

1. Use the VS Code Dev Container (recommended for development)

   - Open the project folder in VS Code.
   - From the Command Palette (Ctrl+Shift+P) choose `Dev Containers: Reopen in Container`.
   - The container will be built from `.devcontainer/Dockerfile` and the `postCreateCommand` will run `scripts/bootstrap_devcontainer.sh` to install dependencies.

2. Use docker-compose for quick runtime testing

   - Make sure Docker Desktop is installed and running on your machine.
   - From the repository root run (PowerShell):

     ```powershell
     .\scripts\devcontainer_build.ps1
     ```

   - Or to only build the images:

     ```powershell
     .\scripts\devcontainer_build.ps1 -BuildOnly
     ```

Notes

- The devcontainer binds `data/`, `models/` and `reports/` from your host into the container so generated artifacts appear locally.

- If you need to provide API keys or secrets, copy `.env.example` to `.env` and fill in values before starting containers.
- If you need to provide API keys or secrets, copy `.env.example` to `.env` and fill in values before starting containers.
