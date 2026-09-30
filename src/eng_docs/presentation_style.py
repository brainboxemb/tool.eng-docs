"""Shared print-friendly presentation style primitives."""
from __future__ import annotations

PALETTES = {
    "neutral": ("#f6f7f8", "#697077", "#2f3337"),
    "active": ("#e8f1fb", "#4b78a8", "#244b73"),
    "success": ("#eaf5e7", "#5a8750", "#31582b"),
    "warning": ("#fff4d6", "#a77a19", "#6a4b00"),
    "danger": ("#fdeaea", "#b14c4c", "#7a2929"),
    "muted": ("#f1f1f1", "#888888", "#555555"),
    "mature": ("#eaf5e7", "#5a8750", "#31582b"),
    "draft": ("#fff4d6", "#a77a19", "#6a4b00"),
}

TEXT = "#2f3337"
TEXT_MUTED = "#626a72"
CARD_STROKE = "#b8c0c8"
RULE = "#d9dde1"
PAGE_BACKGROUND = "#ffffff"
CARD_BACKGROUND = "#ffffff"


def palette(tone):
    return PALETTES.get(tone or "neutral", PALETTES["neutral"])


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16) / 255.0 for i in (0, 2, 4))
