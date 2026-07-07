#!/bin/sh
set -eu

url="${1:-file:///home/pi/device-monitor-dashboard.html}"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export DISPLAY="${DISPLAY:-:0}"

pkill -x chromium 2>/dev/null || true
sleep 1

exec chromium \
  --ozone-platform=x11 \
  --kiosk \
  --start-fullscreen \
  --window-position=0,0 \
  --window-size=803,602 \
  --no-first-run \
  --no-default-browser-check \
  --password-store=basic \
  "$url"
