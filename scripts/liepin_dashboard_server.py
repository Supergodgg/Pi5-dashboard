#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "127.0.0.1"
PORT = 8787
BASE_DIR = Path("/home/pi/zhaopin-automation")
RUN_SCRIPT = Path("/home/pi/lp")
PID_FILE = BASE_DIR / "liepin.pid"
STATE_FILE = Path("/tmp/liepin-dashboard.js")
schedule_lock = threading.Lock()
scheduled_timer = None
scheduled_at = None
scheduled_limit = None
scheduled_mode = None
scheduled_days = []
scheduled_time = None


DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def read_pid():
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def is_running(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def write_control_state(message, running=None):
    state = {
        "running": bool(running) if running is not None else is_running(read_pid()),
        "phase": "控制台",
        "target": 30,
        "collected": 0,
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "lastLog": message,
        "updatedAt": "--",
        "scheduledAt": scheduled_at,
        "scheduledLimit": scheduled_limit,
        "scheduledMode": scheduled_mode,
        "scheduledDays": scheduled_days,
        "scheduledTime": scheduled_time,
    }
    try:
        STATE_FILE.write_text(
            "window.__LIEPIN_AUTOMATION__ = "
            + json.dumps(state, ensure_ascii=False)
            + ";\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def normalize_schedule(mode, days):
    if mode == "daily":
        return list(range(7))
    if mode == "workdays":
        return list(range(5))
    if mode == "weekend":
        return [5, 6]
    normalized = []
    for day in days or []:
        try:
            day = int(day)
        except Exception:
            continue
        if 0 <= day <= 6 and day not in normalized:
            normalized.append(day)
    return sorted(normalized)


def schedule_label(mode, days, run_time):
    if mode == "daily":
        day_text = "每天"
    elif mode == "workdays":
        day_text = "工作日"
    elif mode == "weekend":
        day_text = "周末"
    else:
        day_text = "、".join(DAY_NAMES[day] for day in days) if days else "未选择周几"
    return f"{day_text} {run_time}"


def next_run_datetime(days, run_time):
    hour, minute = [int(part) for part in run_time.split(":", 1)]
    now = datetime.now()
    for offset in range(8):
        candidate_date = now.date() + timedelta(days=offset)
        if candidate_date.weekday() not in days:
            continue
        candidate = datetime.combine(candidate_date, datetime.min.time()).replace(hour=hour, minute=minute)
        if candidate > now:
            return candidate
    raise ValueError("no_future_run_time")


class Handler(BaseHTTPRequestHandler):
    def _headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, payload, status=200):
        self._headers(status)
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._headers()

    def do_GET(self):
        if self.path != "/status":
            self._json({"ok": False, "error": "not_found"}, status=404)
            return
        pid = read_pid()
        self._json({
            "ok": True,
            "running": is_running(pid),
            "pid": pid,
            "scheduledAt": scheduled_at,
            "scheduledLimit": scheduled_limit,
        })

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}

        if self.path == "/start":
            self.start_liepin(payload)
            return
        if self.path == "/stop":
            self.stop_liepin()
            return
        if self.path == "/schedule":
            self.schedule_liepin(payload)
            return
        if self.path == "/cancel-schedule":
            self.cancel_schedule()
            return
        self._json({"ok": False, "error": "not_found"}, status=404)

    def run_liepin(self, limit):
        current_pid = read_pid()
        if is_running(current_pid):
            return {"ok": False, "error": "already_running", "pid": current_pid}

        completed = subprocess.run(
            [str(RUN_SCRIPT), str(limit)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        pid = read_pid()
        if completed.returncode != 0:
            return {
                "ok": False,
                "error": "start_failed",
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }

        write_control_state(f"已从 dashboard 启动猎聘自动投递，数量 {limit}。", running=True)
        return {"ok": True, "pid": pid, "limit": limit, "stdout": completed.stdout}

    def start_liepin(self, payload):
        limit = payload.get("limit", 30)
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
        except Exception:
            self._json({"ok": False, "error": "invalid_limit"}, status=400)
            return

        result = self.run_liepin(limit)
        if not result.get("ok"):
            status = 409 if result.get("error") == "already_running" else 500
            self._json(result, status=status)
            return
        self._json(result)

    def stop_liepin(self):
        pid = read_pid()
        if not is_running(pid):
            subprocess.run(
                ["pkill", "-f", "zhaopin-automation-chromium"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            self._json({"ok": True, "running": False, "message": "not_running"})
            return
        try:
            os.kill(pid, signal.SIGTERM)
            subprocess.run(
                ["pkill", "-f", "zhaopin-automation-chromium"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            write_control_state("已从 dashboard 请求停止猎聘自动投递。", running=False)
            self._json({"ok": True, "stopped": True, "pid": pid})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, status=500)

    def schedule_liepin(self, payload):
        global scheduled_timer, scheduled_at, scheduled_limit, scheduled_mode, scheduled_days, scheduled_time
        limit = payload.get("limit", 30)
        mode = payload.get("mode", "daily")
        run_time = payload.get("time")
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
        except Exception:
            self._json({"ok": False, "error": "invalid_limit"}, status=400)
            return
        try:
            if not isinstance(run_time, str) or len(run_time.split(":")) != 2:
                raise ValueError
            hour, minute = [int(part) for part in run_time.split(":", 1)]
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except Exception:
            self._json({"ok": False, "error": "invalid_time"}, status=400)
            return
        days = normalize_schedule(mode, payload.get("days", []))
        if not days:
            self._json({"ok": False, "error": "no_days_selected"}, status=400)
            return

        def arm_next():
            global scheduled_timer, scheduled_at
            next_dt = next_run_datetime(scheduled_days, scheduled_time)
            scheduled_at = next_dt.strftime("%Y-%m-%d %H:%M")
            delay = max(1, next_dt.timestamp() - time.time())
            scheduled_timer = threading.Timer(delay, fire)
            scheduled_timer.daemon = True
            scheduled_timer.start()

        def fire():
            global scheduled_timer
            with schedule_lock:
                scheduled_timer = None
                fire_limit = scheduled_limit or limit
            result = self.run_liepin(fire_limit)
            if not result.get("ok"):
                write_control_state(f"定时启动失败: {result.get('error')}", running=False)
            with schedule_lock:
                if scheduled_mode and scheduled_days and scheduled_time:
                    arm_next()
                    write_control_state(
                        f"已完成一次定时触发，下一次: {scheduled_at}。",
                        running=False,
                    )

        with schedule_lock:
            if scheduled_timer:
                scheduled_timer.cancel()
            scheduled_limit = limit
            scheduled_mode = mode
            scheduled_days = days
            scheduled_time = f"{hour:02d}:{minute:02d}"
            arm_next()

        label = schedule_label(mode, days, scheduled_time)
        write_control_state(
            f"已设置循环定时: {label}，数量 {limit}。下一次: {scheduled_at}。",
            running=False,
        )
        self._json({
            "ok": True,
            "scheduledAt": scheduled_at,
            "scheduledLabel": label,
            "limit": limit,
        })

    def cancel_schedule(self):
        global scheduled_timer, scheduled_at, scheduled_limit, scheduled_mode, scheduled_days, scheduled_time
        with schedule_lock:
            if scheduled_timer:
                scheduled_timer.cancel()
            scheduled_timer = None
            scheduled_at = None
            scheduled_limit = None
            scheduled_mode = None
            scheduled_days = []
            scheduled_time = None
        write_control_state("已取消猎聘自动投递定时任务。", running=False)
        self._json({"ok": True, "cancelled": True})

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
