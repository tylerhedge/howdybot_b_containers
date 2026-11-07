# HowdyBot software — containers

One Dockerfile produces both the **dev container** (any laptop) and the **robot image** (Jetson Orin Nano). They share the same Ubuntu 24.04 + ROS 2 Jazzy layers, so "works in dev" means "works on the robot" except for real hardware and the GPU.

## Platform

| | Version |
|---|---|
| JetPack | 7.2.x (Jetson Linux R39, Ubuntu 24.04, CUDA 13) |
| ROS 2 | Jazzy |
| Robot base image | `nvcr.io/nvidia/cuda:13.0.0-runtime-ubuntu24.04` (arm64) |
| Dev base image | `ubuntu:24.04` (amd64 or arm64) |

JetPack 7.2 moved the Orin family to the same "SBSA" CUDA stack as servers, so standard NVIDIA arm64 images from NGC work on the Jetson — NVIDIA no longer publishes the old `l4t-*` images.

## How the Dockerfile is built (read this once)

```
manifests ─┐ (only package.xml files)
base ──────┴─> deps-run ──> deps-build ──┬──> dev        (laptops)
                   │                     └──> build ──┐
                   └──────────────────────────────────┴──> runtime  (Jetson)
```

* **Stages** are layered images; `--target dev` or `--target runtime` picks which one you get. Default target = `runtime`.
* **Layer caching:** Docker reuses a layer if its inputs didn't change. Slow things (apt, rosdep) come first; fast-changing things (our code) come last. The `manifests` trick means editing a `.py` file never re-runs `rosdep install` — only editing a `package.xml` does.
* **Cache mounts** (`--mount=type=cache`) keep downloaded `.deb` files between builds without putting them in the image. Side effect: run `sudo apt-get update` before `apt install` inside a container.
* **Dependencies:** declare them in `package.xml` (`<exec_depend>` for runtime, `<depend>`/`<build_depend>` for compiling). rosdep reads them and installs them in the image. Anything not tied to a package goes in `docker/apt/*.txt`.

## Day-to-day development (no hardware needed)

1. Install Docker Desktop (or Docker Engine on Linux) and VS Code with the *Dev Containers* extension.
2. Open the repo → **Reopen in Container**. First build is ~10–20 min; after that it's seconds.
3. The repo is mounted at `/home/ros/howdybot`. Build with `cb` (alias for `colcon build --symlink-install` in `ws/`).
4. Try it: `ros2 launch howdybot_bringup robot.launch.py`, then in another terminal `ros2 topic echo /howdy/heartbeat`.

**Visualization:** RViz/Gazebo windows work on Linux and Windows (WSL2) via X11. On macOS, use Foxglove Studio connected to `ws://localhost:8765` (the launch file starts `foxglove_bridge`). Foxglove is also the easiest way to look at the real robot from a laptop.

**Test the actual robot image without the robot:**
```bash
make robot-local   # builds the arm64 image on your laptop (emulated, slow but works)
make robot-test    # runs it; you should see "Howdy! Running on aarch64"
```
No GPU under emulation, but it proves the image builds, installs, and launches.

## Commissioning the Jetson (target: < 30 min)

**Before hardware arrives:** push to `main` → GitHub Actions builds `ghcr.io/<owner>/howdybot:robot` and `:dev`. Set `HOWDYBOT_IMAGE` in `.env.example` to that name.

**When it arrives:**
1. **Firmware:** a factory Orin Nano dev kit may need its UEFI/QSPI firmware updated through a JetPack 6.x image *before* the JetPack 7.2.1 ISO will boot. Follow NVIDIA's Orin Nano getting-started guide for this step.
2. Flash JetPack 7.2.1 from the ISO on a USB stick (there's no SD-card image in JetPack 7). Install to an NVMe SSD if you have one.
3. ```bash
   git clone <this repo> ~/howdybot && cd ~/howdybot
   ./scripts/jetson-bootstrap.sh --headless
   ```
   This installs/configures Docker + GPU access, installs udev rules, pulls the image, and starts the robot container with `restart: unless-stopped` so it launches on every boot. Private repo? Run `sudo docker login ghcr.io` with a GitHub token first.

**Updating the robot later:** push code → wait for CI → on the Jetson run `make deploy`.

## Files

| Path | What |
|---|---|
| `docker/Dockerfile` | All image stages |
| `docker/apt/{base,build,dev}.txt` | Extra apt packages per stage |
| `docker/ros_entrypoint.sh` | Sources ROS + workspace before any command |
| `docker/udev/` | Stable device names for the two LiDARs (template) |
| `compose.yaml` | `robot` service (Jetson) and `dev` service (laptops) |
| `.devcontainer/devcontainer.json` | VS Code dev container |
| `.github/workflows/images.yml` | CI build + push to ghcr.io |
| `scripts/jetson-bootstrap.sh` | One-shot Jetson setup |
| `config/`, `data/` | Mounted into the robot container: params/audio (edit without rebuilding), logs/bags |
| `ws/src/howdybot_bringup` | Placeholder package + `robot.launch.py` (what the robot runs) |

## Known TODOs

* Add sensor driver packages to `howdybot_bringup/package.xml` once LiDAR/camera models are final, and fill in the udev rules.
* `privileged: true` is the quick way to reach USB devices; replace with specific `devices:` entries once hardware is fixed.
* If you adopt NVIDIA Isaac ROS for GPU person detection, version 4.6 is the release that targets JetPack 7.2 + Jazzy; you may base the robot image on theirs instead.
* Pin `ROS_APT_SOURCE_VERSION` and base image digests before the final demo for fully reproducible builds.
