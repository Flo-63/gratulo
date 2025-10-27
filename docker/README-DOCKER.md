# 🐳 GRATULO Docker Setup

This setup allows running **gratulo** in clearly separated Docker environments:
- **Development (`dev`)** → Live mount with automatic reloading  
- **Test (`test`)** → Fresh build without mounts  
- **Public Release (`public`)** → Use of the published Docker image  
- **Down / Wipe** → Stop or completely remove all containers and volumes  

All management is handled via a **single script**:  
`compose.sh` (Linux/macOS) or `compose.bat` (Windows).

---

## Directory Structure

```
gratulo/
└── docker/
    ├── docker-compose.yml          # Base setup (Redis, volumes, service)
    ├── docker-compose.dev.yml      # Development overrides
    ├── docker-compose.test.yml     # Test overrides (build without mounts)
    ├── docker-compose.public.yml   # Overrides for public release usage
    ├── .env.base                   # Shared base configuration
    ├── .env.dev                    # Development configuration (optional)
    ├── .env.test                   # Test configuration (optional)
    ├── .env.public                 # Configuration for public release (optional)
    ├── compose.sh                  # Universal script (Linux/macOS)
    ├── compose.bat                 # Universal script (Windows)
    └── README.md
```

---

## Usage

### Linux / macOS

```bash
./docker/compose.sh dev      # Development (with hot reload)
./docker/compose.sh test     # Test (build without mounts)
./docker/compose.sh public   # Start public release image
./docker/compose.sh down     # Stop containers (keep data)
./docker/compose.sh wipe     # Delete containers and volumes (with confirmation)
```

### Windows (CMD or PowerShell)

```bat
docker\compose dev
docker\compose test
docker\compose public
docker\compose down
docker\compose wipe
```

**Note:**

All Compose scripts are located in the /docker directory.
They can be executed from anywhere (for example, from the project root as shown here),
because they automatically switch to their own directory when run.
---

## Environment Files

### Basic Concept

- The file **`.env.base`** is **always** loaded.  
- The file **`.env.<mode>`** (`.env.dev`, `.env.test`, `.env.public`) is **optional**.  
- If it doesn't exist, the setup continues with a warning.

**Example output if `.env.test` is missing:**
```
No specific .env for 'test' found – using only .env.base
```

---

### Example `.env.base`

```bash
REDIS_HOST=redis
REDIS_PORT=6379
APP_NAME=gratulo
```

### Example `.env.dev`

```bash
DEBUG=true
APP_SECRET_KEY=<dev-secret>
```

### Example `.env.public`

```bash
DEBUG=false
APP_SECRET_KEY=<prod-secret>
```

---

## Environment Overview

| Environment | Mounts | Build | Reload | Description |
|--------------|--------|--------|--------|--------------|
| **dev**      | ✅ Yes (`.:/app`) | ❌ No | 🔁 Auto | Live reload with local code |
| **test**     | ❌ No | ✅ Yes | ❌ No | Production-like build |
| **public**   | ❌ No | ❌ No | ❌ No | Use of published release image |

## Note for Windows Developers

The automatic reload feature in development mode (`compose.sh dev`) only works
if the project files are located on the WSL file system (e.g. `/home/<user>/projects/gratulo`).

**Reason:**
Docker Desktop mounts Windows drives (`C:\`, `D:\`, etc.) using a network file system
that does not propagate file change events to Linux. As a result, `uvicorn` or `watchfiles`
cannot detect source code changes when running from NTFS.

**Recommendation:**
Move the project into WSL:

```bash
mkdir -p ~/projects
cp -r /mnt/d/Python/gratulo ~/projects/
```

Then adjust the mounts in docker-compose.dev.yml:
```yaml
volumes:
  - ~/projects/gratulo/app:/app/app
  - ~/projects/gratulo/frontend:/app/frontend
```

---

## Explanation: Mount vs. Build

### Development
```yaml
volumes:
  - .:/app
command: uvicorn app.main:app --reload
```

- The local code is **mounted directly** into the container (bind mount).  
- Changes in backend or frontend are applied immediately if you are using Linux or WSL (See remark above)
- `docker compose down -v` does **not** remove your code since it's on the host.

---

### Test
```yaml
build:
  context: ..
```

- No mount → container uses the **locally built image**.  
- Same behavior as in production.  
- Ideal for CI/CD or integration tests.

---

### Public
```yaml
image: florianmoesch/gratulo:latest
```

- Container uses the **publicly released image** from Docker Hub.  
- No local files are mounted.  
- Stable, safe, and reproducible.

---

## Stop & Clean Up

### Stop Containers (keep data)
```bash
./compose.sh down
```

### Delete Containers + Volumes (with confirmation)
```bash
./compose.sh wipe
```

You will be asked:
```
You are about to delete ALL containers, networks and volumes!
Are you sure you want to continue? (yes/NO):
```

Only entering **yes** will delete volumes.

---

## Example Workflows

### Development
```bash
./compose.sh dev
# → Starts containers with hot reload and live mounts
```

### Test
```bash
./compose.sh test
# → Builds containers without local mounts
```

### Public Release
```bash
./compose.sh public
# → Starts containers using the released image
```

---

## Tips & Best Practices

- Use `.env.base` for shared variables (e.g., Redis, ports).  
- `.env.dev`, `.env.test`, `.env.public` should contain only environment-specific differences.  
- Run `./compose.sh test` before every release to detect build issues early.  
- `./compose.sh wipe` includes a confirmation step to prevent data loss.  
- Both scripts behave identically on **Windows and Linux/macOS**.  

---

## Example Outputs

### When `.env.dev` exists:
```
Using environment files: .env.base + .env.dev
Starting GRATULO in development mode...
```

### When `.env.dev` is missing:
```
No specific .env for 'dev' found – using only .env.base
Starting GRATULO in development mode...
```

---

## Language Selection

Both scripts (`compose.sh` and `compose.bat`) support **bilingual output** (German/English).

The language can be set via a constant at the top of each script:

### Linux/macOS
```bash
LANGUAGE="en"   # or "de"
```

### Windows
```bat
set LANGUAGE=en
```

All messages (help, info, warnings) are displayed in the chosen language.  
Both scripts are **ASCII-only** and compatible with all terminals.

---

## Note

This setup was created to:
- Provide unified Docker workflows for **development, testing and public release**
- Ensure safe volume handling  
- Support `.env` inheritance without breaking builds  
- Behave identically on **Linux/macOS and Windows**

**Last updated:** October 2025  
**Maintainer:** Florian M.

---

> “A clean Docker setup is not a luxury – it’s the foundation of stability.”
