import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

import keyboard
import mss
import numpy as np
import yaml

from input_click import ClickGuard, click_screen_point
from vision import load_template, match_accept_button_with_metrics, scales_from_config, to_gray
from window_probe import find_window_by_title_substring, get_client_region, get_window_title


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config missing: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def run() -> int:
    cfg = load_config()
    setup_logging(cfg.get("log_level", "INFO"))

    title_substring = str(cfg.get("window_title_contains", "League of Legends"))
    in_game_title_keywords = [
        str(x).lower()
        for x in cfg.get(
            "in_game_title_keywords",
            ["(tm) client", "league of legends.exe"],
        )
    ]
    threshold = float(cfg.get("match_threshold", 0.86))
    poll_interval = float(cfg.get("poll_interval_ms", 700)) / 1000.0
    heartbeat_interval = float(cfg.get("heartbeat_interval_sec", 5.0))
    stop_hotkey = str(cfg.get("hotkey_stop", "f10"))
    click_guard = ClickGuard(cooldown_sec=float(cfg.get("click_cooldown_sec", 8.0)))

    multi_scale_cfg = cfg.get("multi_scale", {}) or {}
    scales = scales_from_config(
        enabled=bool(multi_scale_cfg.get("enabled", True)),
        config_scales=list(multi_scale_cfg.get("scales", [1.0])),
    )

    template = load_template(str(cfg.get("template_path", "assets/accept_template.png")))
    logging.info("Started. stop_hotkey=%s threshold=%.3f scales=%s", stop_hotkey, threshold, scales)

    stop = {"value": False}

    def on_stop() -> None:
        stop["value"] = True
        logging.info("Stop requested by hotkey.")

    keyboard.add_hotkey(stop_hotkey, on_stop)
    in_game_paused = False
    app_state = "init"
    last_window_title = "none"
    last_heartbeat_ts = 0.0

    def heartbeat(force: bool = False) -> None:
        nonlocal last_heartbeat_ts
        now = time.time()
        if force or (now - last_heartbeat_ts) >= heartbeat_interval:
            logging.info("Heartbeat window='%s' state='%s'", last_window_title, app_state)
            last_heartbeat_ts = now

    with mss.mss() as sct:
        while not stop["value"]:
            hwnd = find_window_by_title_substring(title_substring)
            if not hwnd:
                in_game_paused = False
                last_window_title = "not_found"
                app_state = "waiting_window"
                heartbeat()
                logging.debug("LoL window not found.")
                time.sleep(poll_interval)
                continue

            current_title = get_window_title(hwnd).lower()
            last_window_title = current_title or "untitled"
            if any(keyword in current_title for keyword in in_game_title_keywords):
                if not in_game_paused:
                    logging.info("In-game window detected (%s). Auto-accept paused.", current_title)
                    in_game_paused = True
                app_state = "paused_in_game"
                heartbeat()
                time.sleep(poll_interval)
                continue
            if in_game_paused:
                logging.info("Client window restored. Auto-accept resumed.")
                in_game_paused = False
            app_state = "scanning_client"
            heartbeat()

            region = get_client_region(hwnd)
            if region is None:
                app_state = "client_region_unavailable"
                heartbeat()
                logging.debug("LoL client region unavailable.")
                time.sleep(poll_interval)
                continue

            monitor = {
                "left": region.left,
                "top": region.top,
                "width": region.width,
                "height": region.height,
            }
            frame = np.array(sct.grab(monitor), dtype=np.uint8)
            frame_bgr = frame[:, :, :3]
            gray = to_gray(frame_bgr)

            result, best_confidence, best_scale = match_accept_button_with_metrics(
                gray_frame=gray,
                template_gray=template,
                threshold=threshold,
                scales=scales,
            )
            logging.debug(
                "Scan metrics threshold=%.3f best_confidence=%.3f best_scale=%.2f",
                threshold,
                best_confidence,
                best_scale,
            )
            if result is None:
                app_state = "scanning_client"
                heartbeat()
                time.sleep(poll_interval)
                continue

            abs_x = region.left + result.center_x
            abs_y = region.top + result.center_y
            if click_guard.can_click():
                click_screen_point(abs_x, abs_y)
                click_guard.mark_clicked()
                app_state = "clicked"
                logging.info(
                    "Accept clicked at (%s,%s). conf=%.3f scale=%.2f",
                    abs_x,
                    abs_y,
                    result.confidence,
                    result.scale,
                )
                heartbeat(force=True)
            else:
                app_state = "cooldown"
                logging.debug("Match found but cooldown active. conf=%.3f", result.confidence)
                heartbeat()

            time.sleep(poll_interval)

    keyboard.clear_all_hotkeys()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        print("Stopped by keyboard interrupt.")
        raise SystemExit(0)
    except Exception as exc:
        print(f"Fatal error: {exc}")
        raise SystemExit(1)
