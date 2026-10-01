#!/usr/bin/env python3
"""Nudge the macOS pointer every 30 seconds, then put it back.

The move is small and returns to the original spot so the cursor does not
drift. Stop with Ctrl+C.

macOS blocks synthetic pointer events until the app that launched Python is
allowed under System Settings → Privacy & Security → Accessibility.

No third-party packages. CoreGraphics is called through ctypes.
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import time
from collections.abc import Callable

DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_PIXELS = 1
SETTLE_SECONDS = 0.05

# CoreGraphics event constants.
_MOUSE_MOVED = 5
_HID_EVENT_TAP = 0
_LEFT_BUTTON = 0

Point = tuple[float, float]
Move = Callable[[Point], None]


class _CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def nudge_target(position: Point, pixels: int) -> Point:
    x, y = position
    return (x + pixels, y)


def jiggle_once(
    position: Point,
    pixels: int,
    move: Move,
    pause: Callable[[float], None],
) -> None:
    """Move the pointer by ``pixels`` and immediately return it."""
    move(nudge_target(position, pixels))
    pause(SETTLE_SECONDS)
    move(position)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move the macOS mouse every 30 seconds."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Seconds between nudges (default: 30).",
    )
    parser.add_argument(
        "--pixels",
        type=int,
        default=DEFAULT_PIXELS,
        help="How far to nudge, in pixels (default: 1).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Nudge a single time and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without moving the pointer.",
    )
    args = parser.parse_args(argv)
    if args.interval <= 0:
        parser.error("--interval must be greater than 0")
    if args.pixels <= 0:
        parser.error("--pixels must be greater than 0")
    return args


def _format_seconds(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(value)


def run(
    args: argparse.Namespace,
    read_position: Callable[[], Point],
    move: Move,
    sleep: Callable[[float], None],
    pause: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> None:
    while True:
        if args.dry_run:
            log(
                "dry-run: nudge "
                f"{args.pixels}px, then wait {_format_seconds(args.interval)}s"
            )
        else:
            start = read_position()
            jiggle_once(start, args.pixels, move, pause)
            log(
                f"Nudged {args.pixels}px and returned to "
                f"({start[0]:.0f}, {start[1]:.0f})."
            )
        if args.once:
            return
        sleep(args.interval)


def _load_coregraphics():
    core_graphics = ctypes.CDLL(
        "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
    )
    core_foundation = ctypes.CDLL(
        "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
    )

    core_graphics.CGEventCreate.argtypes = [ctypes.c_void_p]
    core_graphics.CGEventCreate.restype = ctypes.c_void_p

    core_graphics.CGEventGetLocation.argtypes = [ctypes.c_void_p]
    core_graphics.CGEventGetLocation.restype = _CGPoint

    core_graphics.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        _CGPoint,
        ctypes.c_uint32,
    ]
    core_graphics.CGEventCreateMouseEvent.restype = ctypes.c_void_p

    core_graphics.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    core_graphics.CGEventPost.restype = None

    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    core_foundation.CFRelease.restype = None
    return core_graphics, core_foundation


def macos_pointer() -> tuple[Callable[[], Point], Move]:
    """Return (read_position, move) backed by macOS CoreGraphics."""
    if sys.platform != "darwin":
        raise SystemExit(
            "This script moves the pointer with macOS CoreGraphics. Run it on a Mac."
        )
    core_graphics, core_foundation = _load_coregraphics()

    def read_position() -> Point:
        event = core_graphics.CGEventCreate(None)
        if not event:
            raise SystemExit("CoreGraphics could not read the pointer position.")
        try:
            point = core_graphics.CGEventGetLocation(event)
        finally:
            core_foundation.CFRelease(event)
        return (point.x, point.y)

    def move(point: Point) -> None:
        event = core_graphics.CGEventCreateMouseEvent(
            None,
            _MOUSE_MOVED,
            _CGPoint(point[0], point[1]),
            _LEFT_BUTTON,
        )
        if not event:
            raise SystemExit("CoreGraphics could not create a mouse-move event.")
        try:
            core_graphics.CGEventPost(_HID_EVENT_TAP, event)
        finally:
            core_foundation.CFRelease(event)

    return read_position, move


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        read_position: Callable[[], Point] = lambda: (0.0, 0.0)
        move: Move = lambda _point: None
    else:
        read_position, move = macos_pointer()
    try:
        run(args, read_position, move, time.sleep, log=print)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
