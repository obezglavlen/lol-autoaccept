from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np


@dataclass
class MatchResult:
    confidence: float
    center_x: int
    center_y: int
    template_w: int
    template_h: int
    scale: float


def load_template(path: str) -> np.ndarray:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Template missing: {p}")
    image = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if image is None or image.size == 0:
        raise ValueError(f"Template unreadable: {p}")
    return image


def to_gray(frame_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)


def _resize_template(template: np.ndarray, scale: float) -> Optional[np.ndarray]:
    if abs(scale - 1.0) < 1e-6:
        return template
    resized = cv2.resize(template, dsize=None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    if resized.shape[0] < 8 or resized.shape[1] < 8:
        return None
    return resized


def match_accept_button(
    gray_frame: np.ndarray,
    template_gray: np.ndarray,
    threshold: float,
    scales: Sequence[float],
) -> Optional[MatchResult]:
    result, _best_confidence, _best_scale = match_accept_button_with_metrics(
        gray_frame=gray_frame,
        template_gray=template_gray,
        threshold=threshold,
        scales=scales,
    )
    return result


def match_accept_button_with_metrics(
    gray_frame: np.ndarray,
    template_gray: np.ndarray,
    threshold: float,
    scales: Sequence[float],
) -> Tuple[Optional[MatchResult], float, float]:
    frame_h, frame_w = gray_frame.shape[:2]
    best: Optional[Tuple[float, int, int, int, int, float]] = None

    for scale in scales:
        scaled_t = _resize_template(template_gray, float(scale))
        if scaled_t is None:
            continue
        t_h, t_w = scaled_t.shape[:2]
        if t_w >= frame_w or t_h >= frame_h:
            continue

        match = cv2.matchTemplate(gray_frame, scaled_t, cv2.TM_CCOEFF_NORMED)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(match)
        if best is None or max_val > best[0]:
            best = (float(max_val), int(max_loc[0]), int(max_loc[1]), int(t_w), int(t_h), float(scale))

    if best is None:
        return None, 0.0, 1.0

    confidence, x, y, t_w, t_h, scale = best
    if confidence < threshold:
        return None, confidence, scale

    return (
        MatchResult(
            confidence=confidence,
            center_x=x + (t_w // 2),
            center_y=y + (t_h // 2),
            template_w=t_w,
            template_h=t_h,
            scale=scale,
        ),
        confidence,
        scale,
    )


def scales_from_config(enabled: bool, config_scales: List[float]) -> List[float]:
    if not enabled:
        return [1.0]
    cleaned = [float(s) for s in config_scales if s > 0.0]
    if 1.0 not in cleaned:
        cleaned.append(1.0)
    return sorted(set(cleaned))
