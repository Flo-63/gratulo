<p align="center">
  <picture>
    <source srcset="frontend/static/images/Logo-tailwindblue.svg" type="image/svg+xml">
    <img src="frontend/static/images/Logo-tailwindblue.png" alt="Gratulo Logo" width="100">
  </picture>
</p>

# 🚀 Quick Start Guide for **gratulo**

Welcome to **gratulo** — this guide shows you how to explore the app **without installing Python or any dependencies**.  
You’ll be up and running in just a few minutes using Docker.

---

# 🐋 Prerequisites: Install Docker

To run **gratulo**, you need a working Docker environment.

---

## 🪟 Windows
1. Download and install **[Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)**.  
2. Start Docker Desktop after installation.  
3. Verify your installation by running:
   ```bash
   docker --version
   ```
   If a version number is displayed, Docker is correctly installed.

> 💡 **Note:**  
> On Windows 10/11 Home, you may need to enable **WSL2 support**.  
> Docker Desktop usually offers to install this automatically.

---

## 🍎 macOS
1. Download **[Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)**.  
2. Install and start the application.  
3. Verify the installation:
   ```bash
   docker --version
   ```

---

## 🐧 Linux
1. Install Docker using your package manager.  
   Examples:
   ```bash
   # Ubuntu / Debian
   sudo apt install docker.io

   # Fedora
   sudo dnf install docker
   ```
2. Start the Docker service:
   ```bash
   sudo systemctl start docker
   ```
3. Optionally, add your user to the Docker group:
   ```bash
   sudo usermod -aG docker $USER
   ```
   (Log out and back in afterwards.)

4. Test your installation:
   ```bash
   docker run hello-world
   ```

## 🧩 1. Prepare Your Environment

Before starting, you need to set up your environment configuration.

1. Copy the base environment file:
   ```bash
   cp docker/.env.example docker/.env.base
   ```
 
   You can use the provided default settings to try **gratulo** locally right away —  
   but **do not use them in a production environment**, as they contain example keys and credentials.

---

## 🐳 2. Start **gratulo**

Start the Docker environment depending on your operating system.

### Linux / macOS
```bash
./docker/compose.sh public
```

### Windows
```bat
docker\compose.bat public
```

Once the containers are running, open your browser and visit:  
👉 **[http://localhost:8000](http://localhost:8000)**

> **Default login:**  
> **User:** `admin@example.com`  
> **Password:** `ChangeMe123!`

---

## ⚙️ 3. Initial Configuration

1. Open the **Config** page in the application. (You’ll find a gear icon ⚙️ or link in the navigation bar.)  
   This section allows you to connect your mail server and customize system settings.

2. Enter your **SMTP server settings** and create your **initial admin account**.

3. After saving, edit your `.env.public` file again and **remove** the following lines:
   ```bash
   INITIAL_ADMIN_USER=
   INITIAL_PASSWORD=
   ```

   This ensures that gratulo uses the configured admin account for authentication.

4. Log out by clicking on the logout icon in the upper right corner, then restart the server to apply the changes:

#### Restart (Linux / macOS)
```bash
./docker/compose.sh down
./docker/compose.sh public
```

#### Restart (Windows)
```bat
docker\compose.bat down
docker\compose.bat public
```

Now you can now log in using your newly created **admin credentials**.

---

## 🧭 4. Next Steps

- Explore the **web interface** and built-in features.  
- Adjust additional settings in `docker/.env.public` as needed.  
- If you make environment changes, restart the server as shown above.

---

## 🧹 5. Stop or Reset the Environment

To stop or completely remove the running containers:

### Linux / macOS
```bash
./docker/compose.sh down       # Stop (keep data)
./docker/compose.sh wipe       # Stop and delete data
```

### Windows
```bat
docker\compose.bat down
docker\compose.bat wipe
```

---

## 📘 More Information

For a detailed overview of Docker environments  
(`dev`, `test`, and `public` modes), see the  
👉 [README-DOCKER_EN.md](./docker/README-DOCKER_EN.md).

For advanced configuration, developer setup, or CI/CD usage,  
refer to the **[developer documentation](./README.md)**.

---

## ✅ Summary

| Step | Task | Command |
|:----:|:--------------------------|:----------------------------------------------------------|
| 1 | Copy base config | `cp docker/.env.example docker/.env.public` |
| 2 | Start gratulo | `./docker/compose.sh public` |
| 3 | Configure SMTP + admin | via browser |
| 4 | Restart environment | `./docker/compose.sh down && ./docker/compose.sh public` |
| 5 | Stop or reset | `./docker/compose.sh down` or `wipe` |

---

> “A clean setup is the foundation of stability.”
