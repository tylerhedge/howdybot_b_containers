#!/usr/bin/env bash
# Sources ROS 2 and whichever HowdyBot workspace exists, then runs the command.
#   robot image: /opt/howdybot/install   (HOWDYBOT_INSTALL)
#   dev image:   $HOWDYBOT_WS/install    (after you run colcon build)
set -e

source "/opt/ros/${ROS_DISTRO}/setup.bash"

if [ -n "${HOWDYBOT_INSTALL:-}" ] && [ -f "${HOWDYBOT_INSTALL}/setup.bash" ]; then
  source "${HOWDYBOT_INSTALL}/setup.bash"
fi
if [ -n "${HOWDYBOT_WS:-}" ] && [ -f "${HOWDYBOT_WS}/install/setup.bash" ]; then
  source "${HOWDYBOT_WS}/install/setup.bash"
fi

exec "$@"
