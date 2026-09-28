"""Behavior tests for the macOS mouse nudge script."""

import pytest

from mac_mouse_move import jiggle_once, main, parse_args, run


def test_default_interval_is_30_seconds():
    args = parse_args([])
    assert args.interval == 30
    assert args.pixels == 1
    assert args.once is False


def test_interval_and_pixels_must_be_positive():
    with pytest.raises(SystemExit):
        parse_args(["--interval", "0"])
    with pytest.raises(SystemExit):
        parse_args(["--pixels", "-2"])


def test_jiggle_moves_away_then_returns_to_the_start():
    calls = []
    pauses = []

    jiggle_once(
        (10, 20),
        pixels=2,
        move=calls.append,
        pause=pauses.append,
    )

    assert calls == [(12, 20), (10, 20)]
    assert pauses == [0.05]


def test_run_nudges_then_waits_30_seconds():
    moves = []
    sleeps = []

    def read_position():
        return (5, 8)

    def stop_after_interval(seconds):
        sleeps.append(seconds)
        raise StopIteration

    with pytest.raises(StopIteration):
        run(
            parse_args([]),
            read_position,
            moves.append,
            stop_after_interval,
            pause=lambda _seconds: None,
            log=lambda _message: None,
        )

    assert moves == [(6, 8), (5, 8)]
    assert sleeps == [30]


def test_run_once_does_not_wait():
    moves = []

    def fail_if_called(_seconds):
        raise AssertionError("should not sleep when --once is set")

    run(
        parse_args(["--once"]),
        lambda: (1, 1),
        moves.append,
        fail_if_called,
        pause=lambda _seconds: None,
        log=lambda _message: None,
    )

    assert moves == [(2, 1), (1, 1)]


def test_dry_run_does_not_move_or_require_macos():
    moves = []

    def fail_if_called():
        raise AssertionError("dry-run must not read the pointer position")

    messages = []

    def stop_after_interval(_seconds):
        raise StopIteration

    with pytest.raises(StopIteration):
        run(
            parse_args(["--dry-run"]),
            fail_if_called,
            moves.append,
            stop_after_interval,
            log=messages.append,
        )

    assert moves == []
    assert messages == ["dry-run: nudge 1px, then wait 30s"]


def test_main_dry_run_once_exits_without_moving(capsys):
    assert main(["--dry-run", "--once"]) == 0
    assert "dry-run: nudge 1px, then wait 30s" in capsys.readouterr().out
