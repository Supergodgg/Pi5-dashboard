#!/bin/bash
# Dashboard Toggle — Ctrl+Alt+D to show/hide the monitoring dashboard
# Uses X11 mode + xdotool F11 to force REAL fullscreen every time

export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0

URL="file:///home/pi/device-monitor-dashboard.html"

if ! pgrep -f "/home/pi/zhaopin-automation/liepin_dashboard_server.py" >/dev/null 2>&1; then
    nohup python3 /home/pi/zhaopin-automation/liepin_dashboard_server.py \
        >/tmp/liepin-dashboard-server.log 2>&1 &
fi
if ! pgrep -f "/home/pi/dashboard-news-fetcher.py --loop" >/dev/null 2>&1; then
    nohup python3 /home/pi/dashboard-news-fetcher.py --loop --interval 600 --region china \
        >/tmp/dashboard-news-fetcher.log 2>&1 &
fi

# Check if dashboard chromium is running (match actual chromium binary, not grep)
DASH_PID=$(ps aux | grep "/chromium" | grep "device-monitor-dashboard" | grep -v grep | awk '{print $2}' | head -1)

if [ -n "$DASH_PID" ]; then
    # Running — kill to hide
    kill $DASH_PID 2>/dev/null
    pkill -f "chromium.*device-monitor-dashboard" 2>/dev/null
    sleep 1
    pkill -9 -f "chromium.*device-monitor-dashboard" 2>/dev/null
    exit 0
fi

# Not running — launch fullscreen via X11 + xdotool F11
# Use setsid to fully detach from the keybinding's process
setsid bash -c '
    export WAYLAND_DISPLAY=wayland-0
    export DISPLAY=:0
    chromium --ozone-platform=x11 --no-first-run \
        --no-default-browser-check --disable-session-crashed-bubble \
        --disable-features=TranslateUI \
        "file:///home/pi/device-monitor-dashboard.html" &
    CHROME_PID=$!
    sleep 4
    xdotool search --sync --onlyvisible --class "chromium" windowactivate key F11 2>/dev/null
    wait $CHROME_PID 2>/dev/null
' >/dev/null 2>&1 &

exit 0
