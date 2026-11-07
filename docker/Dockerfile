# syntax=docker/dockerfile:1
#
# HowdyBot images — ONE Dockerfile, several targets:
#
#   manifests   tiny helper stage: just the package.xml files from ws/src
#   base        Ubuntu 24.04 + ROS 2 Jazzy + packages both dev and robot need
#   deps-run    base + runtime (exec) deps of OUR packages, resolved by rosdep
#   deps-build  deps-run + compilers + build/test deps
#   dev         deps-build + GUI/sim/debug tools     -> dev container (laptops)
#   build       deps-build + our source, colcon build (throwaway stage)
#   runtime     deps-run + the compiled install/     -> what runs on the Jetson
#
# The only difference between the laptop and the robot is BASE_IMAGE:
#   laptop : ubuntu:24.04                                   (amd64 or arm64)
#   jetson : nvcr.io/nvidia/cuda:13.0.0-runtime-ubuntu24.04 (arm64, JetPack 7.2+)
# Both are Ubuntu 24.04 (noble), so the same apt/ROS packages install on each.

ARG BASE_IMAGE=ubuntu:24.04
ARG ROS_DISTRO=jazzy

###############################################################################
# manifests: copy the source tree, then delete everything except package.xml.
# Downstream stages COPY from here, so the slow `rosdep install` layer only
# re-runs when a package.xml changes — not on every .py/.cpp edit.
# --platform=$BUILDPLATFORM: always runs natively, even when cross-building.
###############################################################################
FROM --platform=$BUILDPLATFORM busybox:stable AS manifests
COPY ws/src /src
RUN find /src -type f ! -name package.xml -delete

###############################################################################
# base
###############################################################################
FROM ${BASE_IMAGE} AS base
ARG ROS_DISTRO
# Leave empty to fetch the newest ros2-apt-source release; pin (e.g. 1.1.0)
# once things work so builds are reproducible.
ARG ROS_APT_SOURCE_VERSION=""

ENV ROS_DISTRO=${ROS_DISTRO} \
    DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=America/Chicago \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Ubuntu images auto-delete the apt cache after every install; turn that off
# so the BuildKit cache mounts below can keep .debs between builds (much
# faster rebuilds, and nothing extra ends up in the image layers).
RUN rm -f /etc/apt/apt.conf.d/docker-clean \
 && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# ROS 2 apt repository (the officially recommended ros2-apt-source package).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg tzdata software-properties-common \
 && add-apt-repository -y universe \
 && ver="${ROS_APT_SOURCE_VERSION:-$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | cut -d'"' -f4)}" \
 && codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")" \
 && curl -fsSL -o /tmp/ros2-apt-source.deb \
      "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ver}/ros2-apt-source_${ver}.${codename}_all.deb" \
 && apt-get install -y /tmp/ros2-apt-source.deb \
 && rm /tmp/ros2-apt-source.deb

# Packages shared by dev + robot. Edit docker/apt/base.txt, not this file.
# (A bind mount reads the list without adding it to the image.)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=bind,source=docker/apt/base.txt,target=/tmp/apt.txt \
    apt-get update \
 && sed -e 's/#.*//' -e '/^[[:space:]]*$/d' /tmp/apt.txt \
    | xargs apt-get install -y --no-install-recommends

RUN rosdep init

# Non-root user "ros" (UID 1000). Ubuntu 24.04 images ship a user "ubuntu"
# that already owns UID 1000, so remove it first.
RUN if id -u ubuntu >/dev/null 2>&1; then userdel -r ubuntu; fi \
 && groupadd --gid 1000 ros \
 && useradd -m -s /bin/bash --uid 1000 --gid 1000 ros \
 && for g in dialout audio video plugdev; do \
        getent group "$g" >/dev/null && usermod -aG "$g" ros; \
    done; true

COPY --chmod=755 docker/ros_entrypoint.sh /ros_entrypoint.sh
ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]

###############################################################################
# deps-run: runtime dependencies declared in OUR package.xml files.
# Add a driver to <exec_depend> in package.xml and it shows up here.
###############################################################################
FROM base AS deps-run
COPY --from=manifests /src /tmp/manifests/src
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
 && rosdep update --rosdistro "$ROS_DISTRO" \
 && rosdep install -y --rosdistro "$ROS_DISTRO" \
      --from-paths /tmp/manifests/src --ignore-src \
      --dependency-types exec

###############################################################################
# deps-build: compilers + build/test dependencies
###############################################################################
FROM deps-run AS deps-build
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=bind,source=docker/apt/build.txt,target=/tmp/apt.txt \
    apt-get update \
 && sed -e 's/#.*//' -e '/^[[:space:]]*$/d' /tmp/apt.txt \
    | xargs apt-get install -y --no-install-recommends \
 && rosdep install -y --rosdistro "$ROS_DISTRO" \
      --from-paths /tmp/manifests/src --ignore-src \
      --dependency-types build --dependency-types buildtool \
      --dependency-types build_export --dependency-types buildtool_export \
      --dependency-types test \
 && rm -rf /tmp/manifests

###############################################################################
# dev: everything a developer wants. Source code is NOT baked in — it is
# bind-mounted from your laptop so edits show up instantly.
###############################################################################
FROM deps-build AS dev
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=bind,source=docker/apt/dev.txt,target=/tmp/apt.txt \
    apt-get update \
 && sed -e 's/#.*//' -e '/^[[:space:]]*$/d' /tmp/apt.txt \
    | xargs apt-get install -y --no-install-recommends

RUN echo 'ros ALL=(root) NOPASSWD:ALL' > /etc/sudoers.d/ros && chmod 0440 /etc/sudoers.d/ros

ENV HOWDYBOT_WS=/home/ros/howdybot/ws
# Interactive VS Code terminals don't go through the entrypoint, so source
# ROS (and our workspace, once built) from .bashrc too.
RUN cat >> /home/ros/.bashrc <<'EOF'
source /opt/ros/$ROS_DISTRO/setup.bash
[ -f "$HOWDYBOT_WS/install/setup.bash" ] && source "$HOWDYBOT_WS/install/setup.bash"
source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash 2>/dev/null || true
alias cb='(cd "$HOWDYBOT_WS" && colcon build --symlink-install)'
EOF

USER ros
RUN rosdep update --rosdistro "$ROS_DISTRO"
WORKDIR /home/ros/howdybot
CMD ["sleep", "infinity"]

###############################################################################
# build: compile our workspace in Release mode (thrown away afterwards)
###############################################################################
FROM deps-build AS build
WORKDIR /opt/howdybot
COPY ws/src src
RUN . "/opt/ros/$ROS_DISTRO/setup.bash" \
 && colcon build --merge-install --install-base /opt/howdybot/install \
      --cmake-args -DCMAKE_BUILD_TYPE=Release \
      --event-handlers console_cohesion+

###############################################################################
# runtime (default target): what runs on the robot. No compilers, no source.
# Runs as root on purpose: simplest access to USB LiDARs, cameras and audio.
###############################################################################
FROM deps-run AS runtime
COPY --from=build /opt/howdybot/install /opt/howdybot/install
ENV HOWDYBOT_INSTALL=/opt/howdybot/install
WORKDIR /opt/howdybot
CMD ["ros2", "launch", "howdybot_bringup", "robot.launch.py"]
