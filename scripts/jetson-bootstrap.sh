#!/usr/bin/env bash
# HowdyBot — one-shot commissioning for a freshly flashed Jetson Orin Nano
# running JetPack 7.2.x (Jetson Linux R39, Ubuntu 24.04).
#
#   git clone <this repo> ~/howdybot && cd ~/howdybot
#   ./scripts/jetson-bootstrap.sh            # add --headless to drop the desktop GUI
#
# Safe to re-run. Run as your normal user; it calls sudo where needed.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEADLESS=0
[[ "${1:-}" == "--headless" ]] && HEADLESS=1

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARNING: %s\033[0m\n' "$*"; }

if [[ $EUID -eq 0 ]]; then
  echo "Run as your normal user (not root); the script uses sudo itself." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
log "1/7 Checking Jetson Linux version"
if [[ -f /etc/nv_tegra_release ]]; then
  head -n1 /etc/nv_tegra_release
  grep -q "R39" /etc/nv_tegra_release || warn "Expected R39 (JetPack 7.2.x). Images are built for Ubuntu 24.04 + SBSA CUDA."
else
  warn "/etc/nv_tegra_release not found — is this a Jetson?"
fi
command -v nvpmodel >/dev/null && sudo nvpmodel -q || true

# ---------------------------------------------------------------------------
log "2/7 Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

# ---------------------------------------------------------------------------
log "3/7 NVIDIA Container Toolkit (GPU access inside containers)"
if ! command -v nvidia-ctk >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y nvidia-container-toolkit
fi
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker

# ---------------------------------------------------------------------------
log "4/7 udev rules (stable /dev names for LiDARs etc.)"
shopt -s nullglob
rules=("$REPO_DIR"/docker/udev/*.rules)
if (( ${#rules[@]} )); then
  sudo cp "${rules[@]}" /etc/udev/rules.d/
  sudo udevadm control --reload-rules && sudo udevadm trigger
  echo "Installed: ${rules[*]##*/}"
else
  echo "No rules in docker/udev/ yet — skipping."
fi

# ---------------------------------------------------------------------------
log "5/7 Smoke test: GPU passthrough"
if sudo docker run --rm --gpus all ubuntu:24.04 bash -c 'echo "GPU passthrough OK"'; then :; else
  warn "GPU passthrough failed. Check: sudo nvidia-ctk runtime configure --runtime=docker"
fi

# ---------------------------------------------------------------------------
log "6/7 Pull and start the robot container"
cd "$REPO_DIR"
[[ -f .env ]] || cp .env.example .env
mkdir -p config data
# shellcheck disable=SC1091
source .env
if [[ "${HOWDYBOT_IMAGE:-}" == *CHANGE_ME* ]]; then
  warn "HOWDYBOT_IMAGE in .env still says CHANGE_ME; building locally instead (slow)."
  sudo docker compose build robot
elif ! sudo docker compose pull robot; then
  warn "Pull failed (private package? run: sudo docker login ghcr.io). Building locally instead."
  sudo docker compose build robot
fi
sudo docker compose up -d robot
sudo docker compose ps

# ---------------------------------------------------------------------------
log "7/7 Optional: headless mode (frees ~1 GB RAM on the 8 GB Orin Nano)"
if (( HEADLESS )); then
  sudo systemctl set-default multi-user.target
  echo "Desktop disabled from next boot. Undo with: sudo systemctl set-default graphical.target"
else
  echo "Skipped (pass --headless to enable)."
fi

log "Done. The robot container now starts automatically on every boot."
echo "Logs:      docker compose logs -f robot"
echo "Shell in:  docker compose exec robot bash"
echo "Log out and back in once so 'docker' works without sudo."
