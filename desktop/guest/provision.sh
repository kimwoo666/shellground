#!/bin/bash
# Image BUILD time only, inside the dedicated guest. Never run on the host.
set -euo pipefail
test "$(cat /opt/shellground/guest-owned)" = shellground-disposable-guest-v1
test -e /dev/virtio-ports/org.shellground.agent
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends bash nano vim-tiny coreutils findutils grep \
  curl wget tar gzip unzip zip dpkg procps psmisc sudo tree less man-db manpages \
  iproute2 net-tools util-linux ca-certificates gnupg python3 docker.io \
  xvfb x11vnc xauth fonts-dejavu-core build-essential cmake python3-pil docker-registry
python3 /opt/shellground/lab.py fixtures
systemctl enable --now docker
usermod -a -G sudo,docker learner
# Use the ROS project's signing key and Ubuntu repository. Retain the installed
# package versions in provisioned.json; do not claim a mutable key URL is pinned.
curl --fail --location --retry 3 https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
guest_arch=$(dpkg --print-architecture)
case "$guest_arch" in amd64|arm64) ;; *) echo "Unsupported training guest architecture: $guest_arch" >&2; exit 1 ;; esac
printf 'deb [arch=%s signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main\n' "$guest_arch" > /etc/apt/sources.list.d/ros2.list
apt-get update
apt-get install -y --no-install-recommends ros-humble-ros-base ros-humble-turtlesim \
  ros-humble-rosbag2 ros-humble-demo-nodes-cpp ros-humble-rqt-graph python3-colcon-common-extensions
systemctl enable --now shellground-display shellground-files
python3 /opt/shellground/offline_repositories.py
python3 -c 'import json, pathlib, subprocess; pathlib.Path("/opt/shellground/provisioned.json").write_text(json.dumps({"protocol":1,"ros":"humble","packages":subprocess.check_output(["dpkg-query","-W"],text=True)}))'
systemctl disable cloud-init cloud-init-local cloud-config cloud-final || true
systemctl disable apt-daily.timer apt-daily-upgrade.timer motd-news.timer \
  update-notifier-download.timer update-notifier-motd.timer || true
systemctl mask systemd-networkd-wait-online.service
sync
