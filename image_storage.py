"""Durable storage helpers for the accept-button template image."""

import os
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps


APP_DIRECTORY_NAME = "LoLAutoAccept"
TEMPLATE_FILENAME = "accept_template.png"
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


def default_template_path():
    """Return a per-user path that remains stable across app restarts."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    base_directory = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return base_directory / APP_DIRECTORY_NAME / TEMPLATE_FILENAME


def first_supported_drop_path(drop_data, splitlist):
    """Return the first supported image path from tkdnd drop data."""
    try:
        raw_paths = splitlist(drop_data)
    except Exception:
        raw_paths = (drop_data,)

    for raw_path in raw_paths:
        candidate = Path(str(raw_path).strip("{}"))
        if candidate.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
            return candidate
    return None


def persist_template(source_path, destination_path):
    """Normalize an image to PNG and atomically save it at destination_path."""
    source = Path(source_path)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")

    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image.save(temporary, format="PNG")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    return destination
