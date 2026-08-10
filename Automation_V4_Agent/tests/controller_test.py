#!/usr/bin/env python3
"""
Controller Navigation Test Script — Automation V4 Agent
=========================================================
Standalone test script that exercises every Xbox controller input through
GIMX without any image/OCR verification.

Run from the repo root:
    python Automation_V4_Agent/tests/controller_test.py
    python Automation_V4_Agent/tests/controller_test.py --console 2
    python Automation_V4_Agent/tests/controller_test.py --suite dpad
    python Automation_V4_Agent/tests/controller_test.py --list-suites

Available test suites:
    all         - Run every suite (default)
    dpad        - D-pad directional navigation
    face        - Face buttons  (A, B, X, Y)
    system      - System buttons (Guide, Menu, View)
    bumpers     - Shoulder buttons + triggers (LB, RB, LT, RT)
    sticks      - Stick clicks + analog movement
    combos      - Multi-button simultaneous presses
    long_press  - Long-press / hold inputs
    sequences   - Realistic Xbox navigation sequences
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Callable

# Make the package importable when run as a script from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Automation_V4_Agent.hardware.gimx_controller import (
    GimxController,
    GimxConfig,
    XboxButton,
    ButtonValue,
)
from Automation_V4_Agent.utils.helpers import wait_ms
from Automation_V4_Agent.utils.logger import setup_logging, get_logger

setup_logging(log_dir="logs")
log = get_logger("controller_test")


# ══════════════════════════════════════════════════════════════════════════════
# Test result tracking
# ══════════════════════════════════════════════════════════════════════════════

class TestResult:
    PASS = "PASS"
    FAIL = "FAIL"


class TestRunner:
    """Runs named test steps and accumulates PASS / FAIL results."""

    def __init__(self, ctrl: GimxController, console: int = 1, dry_run: bool = False):
        self.ctrl     = ctrl
        self.console  = console
        self.dry_run  = dry_run
        self._results: list[dict] = []
        self._suite   = ""

    def suite(self, name: str):
        """Mark the start of a named test suite."""
        self._suite = name
        print(f"\n{'=' * 60}")
        print(f"  Suite: {name}")
        print(f"{'=' * 60}")

    def step(self, name: str, action: Callable, post_delay_ms: int = 500):
        """
        Execute one test step, log PASS or FAIL.

        Args:
            name:          Human-readable label.
            action:        Zero-argument callable that sends controller input.
            post_delay_ms: Wait (ms) after the action before the next step.
        """
        label = f"[{self._suite}] {name}"
        try:
            if not self.dry_run:
                action()
                wait_ms(post_delay_ms)
            status = TestResult.PASS
            log.info(f"  {status}  {label}")
            print(f"  {status:<6}  {label}")
        except Exception as exc:
            status = TestResult.FAIL
            log.error(f"  {status}  {label}  ->  {exc}")
            print(f"  {status:<6}  {label}  ->  {exc}")
        self._results.append({"suite": self._suite, "step": name, "status": status})

    def summary(self) -> int:
        """Print final PASS/FAIL summary. Returns 0 if all passed, 1 otherwise."""
        total   = len(self._results)
        passed  = sum(1 for r in self._results if r["status"] == TestResult.PASS)
        failed  = total - passed
        print(f"\n{'=' * 60}")
        print(f"  CONTROLLER TEST SUMMARY")
        print(f"{'=' * 60}")
        print(f"  Total  : {total}")
        print(f"  PASS   : {passed}")
        print(f"  FAIL   : {failed}")
        print(f"  Result : {'ALL PASS' if failed == 0 else f'{failed} FAILED'}")
        print(f"{'=' * 60}\n")
        if failed:
            print("  Failed steps:")
            for r in self._results:
                if r["status"] == TestResult.FAIL:
                    print(f"    - [{r['suite']}] {r['step']}")
            print()
        return 0 if failed == 0 else 1


# ══════════════════════════════════════════════════════════════════════════════
# Suite: D-Pad
# ══════════════════════════════════════════════════════════════════════════════

def suite_dpad(runner: TestRunner):
    """D-pad directional navigation."""
    c = runner.console
    runner.suite("D-Pad Navigation")
    runner.step("D-pad UP",    lambda: runner.ctrl.short_press(XboxButton.UP,    c))
    runner.step("D-pad DOWN",  lambda: runner.ctrl.short_press(XboxButton.DOWN,  c))
    runner.step("D-pad LEFT",  lambda: runner.ctrl.short_press(XboxButton.LEFT,  c))
    runner.step("D-pad RIGHT", lambda: runner.ctrl.short_press(XboxButton.RIGHT, c))
    runner.step("D-pad UP x3",    lambda: [runner.ctrl.short_press(XboxButton.UP,    c) for _ in range(3)])
    runner.step("D-pad DOWN x3",  lambda: [runner.ctrl.short_press(XboxButton.DOWN,  c) for _ in range(3)])
    runner.step("D-pad LEFT x3",  lambda: [runner.ctrl.short_press(XboxButton.LEFT,  c) for _ in range(3)])
    runner.step("D-pad RIGHT x3", lambda: [runner.ctrl.short_press(XboxButton.RIGHT, c) for _ in range(3)])
    runner.step("D-pad clockwise circle", lambda: [
        runner.ctrl.short_press(btn, c)
        for btn in [XboxButton.UP, XboxButton.RIGHT, XboxButton.DOWN, XboxButton.LEFT]
    ])


# ══════════════════════════════════════════════════════════════════════════════
# Suite: Face Buttons
# ══════════════════════════════════════════════════════════════════════════════

def suite_face_buttons(runner: TestRunner):
    """Face buttons A / B / X / Y — confirm, cancel, and action inputs."""
    c = runner.console
    runner.suite("Face Buttons")
    runner.step("A (confirm)",     lambda: runner.ctrl.short_press(XboxButton.A, c))
    runner.step("B (back/cancel)", lambda: runner.ctrl.short_press(XboxButton.B, c))
    runner.step("X (action)",      lambda: runner.ctrl.short_press(XboxButton.X, c))
    runner.step("Y (action)",      lambda: runner.ctrl.short_press(XboxButton.Y, c))
    runner.step("A double-tap (confirm dialog)", lambda: [
        runner.ctrl.short_press(XboxButton.A, c), wait_ms(300),
        runner.ctrl.short_press(XboxButton.A, c),
    ])
    runner.step("B then A (cancel then confirm)", lambda: [
        runner.ctrl.short_press(XboxButton.B, c), wait_ms(500),
        runner.ctrl.short_press(XboxButton.A, c),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# Suite: System Buttons
# ══════════════════════════════════════════════════════════════════════════════

def suite_system_buttons(runner: TestRunner):
    """System buttons: Guide (Xbox), Menu (hamburger), View (Select)."""
    c = runner.console
    runner.suite("System Buttons")
    runner.step("Guide — open overlay",
                lambda: runner.ctrl.short_press(XboxButton.GUIDE, c), post_delay_ms=2000)
    runner.step("B — dismiss Guide",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)
    runner.step("Menu — context menu",
                lambda: runner.ctrl.short_press(XboxButton.MENU, c), post_delay_ms=1000)
    runner.step("B — dismiss menu",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=500)
    runner.step("View — toggle view/filter",
                lambda: runner.ctrl.short_press(XboxButton.VIEW, c), post_delay_ms=500)
    runner.step("B — dismiss",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=500)

# ══════════════════════════════════════════════════════════════════════════════
# Suite: Bumpers and Triggers
# ══════════════════════════════════════════════════════════════════════════════

def suite_bumpers_triggers(runner: TestRunner):
    """LB / RB shoulder buttons and LT / RT trigger axes."""
    c = runner.console
    runner.suite("Bumpers and Triggers")
    runner.step("LB",  lambda: runner.ctrl.short_press(XboxButton.LB, c))
    runner.step("RB",  lambda: runner.ctrl.short_press(XboxButton.RB, c))
    runner.step("LT",  lambda: runner.ctrl.short_press(XboxButton.LT, c))
    runner.step("RT",  lambda: runner.ctrl.short_press(XboxButton.RT, c))
    runner.step("RB x3 — tab right", lambda: [runner.ctrl.short_press(XboxButton.RB, c) for _ in range(3)])
    runner.step("LB x3 — tab left",  lambda: [runner.ctrl.short_press(XboxButton.LB, c) for _ in range(3)])
    runner.step("LT full axis press",  lambda: runner.ctrl.send_axis(XboxButton.LT, ButtonValue.TRIGGER_FULL_PRESS))
    runner.step("LT axis release",     lambda: runner.ctrl.send_axis(XboxButton.LT, ButtonValue.RELEASED))
    runner.step("RT full axis press",  lambda: runner.ctrl.send_axis(XboxButton.RT, ButtonValue.TRIGGER_FULL_PRESS))
    runner.step("RT axis release",     lambda: runner.ctrl.send_axis(XboxButton.RT, ButtonValue.RELEASED))




# ══════════════════════════════════════════════════════════════════════════════
# Suite: Analog Sticks
# ══════════════════════════════════════════════════════════════════════════════

def suite_sticks(runner: TestRunner):
    """Stick clicks and full-range analog axis movement."""
    c = runner.console
    runner.suite("Analog Sticks")
    runner.step("LS click",  lambda: runner.ctrl.short_press(XboxButton.LS, c))
    runner.step("RS click",  lambda: runner.ctrl.short_press(XboxButton.RS, c))
    runner.step("Left stick full UP",    lambda: runner.ctrl.move_stick(XboxButton.LEFT_STICK_Y, ButtonValue.STICK_FULL_UP))
    runner.step("Left stick full DOWN",  lambda: runner.ctrl.move_stick(XboxButton.LEFT_STICK_Y, ButtonValue.STICK_FULL_DOWN))
    runner.step("Left stick full LEFT",  lambda: runner.ctrl.move_stick(XboxButton.LEFT_STICK_X, ButtonValue.STICK_FULL_LEFT))
    runner.step("Left stick full RIGHT", lambda: runner.ctrl.move_stick(XboxButton.LEFT_STICK_X, ButtonValue.STICK_FULL_RIGHT))
    runner.step("Right stick full UP",    lambda: runner.ctrl.move_stick(XboxButton.RIGHT_STICK_Y, ButtonValue.STICK_FULL_UP))
    runner.step("Right stick full DOWN",  lambda: runner.ctrl.move_stick(XboxButton.RIGHT_STICK_Y, ButtonValue.STICK_FULL_DOWN))
    runner.step("Right stick full LEFT",  lambda: runner.ctrl.move_stick(XboxButton.RIGHT_STICK_X, ButtonValue.STICK_FULL_LEFT))
    runner.step("Right stick full RIGHT", lambda: runner.ctrl.move_stick(XboxButton.RIGHT_STICK_X, ButtonValue.STICK_FULL_RIGHT))
    runner.step("Left stick 50% right+down (diagonal)", lambda: runner.ctrl.left_stick_input(x=50,  y=50))
    runner.step("Left stick neutral",                   lambda: runner.ctrl.left_stick_input(x=0,   y=0))
    runner.step("Right stick 50% right+up (diagonal)",  lambda: runner.ctrl.right_stick_input(x=50, y=-50))
    runner.step("Right stick neutral",                  lambda: runner.ctrl.right_stick_input(x=0,  y=0))




# ══════════════════════════════════════════════════════════════════════════════
# Suite: Combos
# ══════════════════════════════════════════════════════════════════════════════

def suite_combos(runner: TestRunner):
    """Multi-button simultaneous presses."""
    c = runner.console
    runner.suite("Combo Presses")
    runner.step("View + Menu (360 Guide)",
                lambda: runner.ctrl.combo_press(XboxButton.VIEW, XboxButton.MENU, c), post_delay_ms=1500)
    runner.step("B — dismiss",  lambda: runner.ctrl.short_press(XboxButton.B, c))
    runner.step("LB + RB",      lambda: runner.ctrl.combo_press(XboxButton.LB, XboxButton.RB, c))
    runner.step("LT + RT",      lambda: runner.ctrl.combo_press(XboxButton.LT, XboxButton.RT, c))
    runner.step("A + B",        lambda: runner.ctrl.combo_press(XboxButton.A,  XboxButton.B,  c))


# ══════════════════════════════════════════════════════════════════════════════
# Suite: Long Press
# ══════════════════════════════════════════════════════════════════════════════

def suite_long_press(runner: TestRunner):
    """Long-press / hold inputs."""
    c = runner.console
    runner.suite("Long Press")
    # 2-second Guide hold: registers the EMUXONE controller with Xbox on first run.
    # Xbox shows "Press Guide for 2 seconds" — this satisfies that requirement.
    runner.step("Long press Guide 2000ms — register controller + power overlay",
                lambda: runner.ctrl.long_press(XboxButton.GUIDE, hold_ms=2000, console=c), post_delay_ms=3000)
    runner.step("B — dismiss",     lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)
    runner.step("Long press Menu 1500ms",
                lambda: runner.ctrl.long_press(XboxButton.MENU, console=c), post_delay_ms=1000)
    runner.step("B — dismiss",     lambda: runner.ctrl.short_press(XboxButton.B, c))
    runner.step("Long press A 2000ms (confirm-and-hold)",
                lambda: runner.ctrl.long_press(XboxButton.A, hold_ms=2000, console=c))
    runner.step("Long press LB 800ms (rewind)",
                lambda: runner.ctrl.long_press(XboxButton.LB, hold_ms=800, console=c))
    runner.step("Long press RB 800ms (fast-forward)",
                lambda: runner.ctrl.long_press(XboxButton.RB, hold_ms=800, console=c))
    runner.step("Long press X 1000ms",
                lambda: runner.ctrl.long_press(XboxButton.X, hold_ms=1000, console=c))



# ══════════════════════════════════════════════════════════════════════════════
# Suite: Navigation Sequences
# ══════════════════════════════════════════════════════════════════════════════

def suite_sequences(runner: TestRunner):
    """Realistic multi-step Xbox navigation sequences (no image verification)."""
    c = runner.console
    runner.suite("Navigation Sequences")

    # SEQ 1 — Go to Xbox Home
    runner.step("SEQ1: Guide — go Home",
                lambda: runner.ctrl.short_press(XboxButton.GUIDE, c), post_delay_ms=3000)

    # SEQ 2 — Navigate Home tiles left/right
    runner.step("SEQ2: RIGHT x3 on Home tiles",
                lambda: [runner.ctrl.short_press(XboxButton.RIGHT, c) for _ in range(3)])
    runner.step("SEQ2: LEFT x3 back",
                lambda: [runner.ctrl.short_press(XboxButton.LEFT, c)  for _ in range(3)])

    # SEQ 3 — Guide overlay -> My games & apps -> back
    runner.step("SEQ3: Guide overlay",
                lambda: runner.ctrl.short_press(XboxButton.GUIDE, c), post_delay_ms=2000)
    runner.step("SEQ3: RIGHT to My games",
                lambda: runner.ctrl.short_press(XboxButton.RIGHT, c))
    runner.step("SEQ3: A — enter My games",
                lambda: runner.ctrl.short_press(XboxButton.A, c), post_delay_ms=2000)
    runner.step("SEQ3: DOWN x3 in game list",
                lambda: [runner.ctrl.short_press(XboxButton.DOWN, c) for _ in range(3)])
    runner.step("SEQ3: B — back to Guide",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)
    runner.step("SEQ3: B — close Guide",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)

    # SEQ 4 — Guide overlay -> Settings tab -> back
    runner.step("SEQ4: Guide overlay",
                lambda: runner.ctrl.short_press(XboxButton.GUIDE, c), post_delay_ms=2000)
    runner.step("SEQ4: RB x4 — Settings tab",
                lambda: [runner.ctrl.short_press(XboxButton.RB, c) for _ in range(4)])
    runner.step("SEQ4: A — enter Settings",
                lambda: runner.ctrl.short_press(XboxButton.A, c), post_delay_ms=2000)
    runner.step("SEQ4: DOWN x2 in Settings",
                lambda: [runner.ctrl.short_press(XboxButton.DOWN, c) for _ in range(2)])
    runner.step("SEQ4: B — back",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)
    runner.step("SEQ4: B — close Guide",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)

    # SEQ 5 — Guide overlay -> Search -> back
    runner.step("SEQ5: Guide overlay",
                lambda: runner.ctrl.short_press(XboxButton.GUIDE, c), post_delay_ms=2000)
    runner.step("SEQ5: RIGHT x2 to Search",
                lambda: [runner.ctrl.short_press(XboxButton.RIGHT, c) for _ in range(2)])
    runner.step("SEQ5: A — open Search",
                lambda: runner.ctrl.short_press(XboxButton.A, c), post_delay_ms=1000)
    runner.step("SEQ5: B — back",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=500)
    runner.step("SEQ5: Guide — return Home",
                lambda: runner.ctrl.short_press(XboxButton.GUIDE, c), post_delay_ms=2000)

    # SEQ 6 — Game-launch pattern (select tile, back without launching)
    runner.step("SEQ6: Guide — Home",
                lambda: runner.ctrl.short_press(XboxButton.GUIDE, c), post_delay_ms=2000)
    runner.step("SEQ6: RIGHT — select game tile",
                lambda: runner.ctrl.short_press(XboxButton.RIGHT, c))
    runner.step("SEQ6: A — highlight game",
                lambda: runner.ctrl.short_press(XboxButton.A, c), post_delay_ms=1000)
    runner.step("SEQ6: B — back (no launch)",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)

    # SEQ 7 — Quit-game pattern (long Guide, navigate, cancel)
    runner.step("SEQ7: Long Guide — power overlay",
                lambda: runner.ctrl.long_press(XboxButton.GUIDE, console=c), post_delay_ms=2000)
    runner.step("SEQ7: DOWN — Quit Game option",
                lambda: runner.ctrl.short_press(XboxButton.DOWN, c))
    runner.step("SEQ7: A — select Quit",
                lambda: runner.ctrl.short_press(XboxButton.A, c), post_delay_ms=1000)
    runner.step("SEQ7: B — cancel (stay in game)",
                lambda: runner.ctrl.short_press(XboxButton.B, c), post_delay_ms=1000)


# ══════════════════════════════════════════════════════════════════════════════
# Suite registry
# ══════════════════════════════════════════════════════════════════════════════

SUITE_MAP = {
    "dpad":       suite_dpad,
    "face":       suite_face_buttons,
    "system":     suite_system_buttons,
    "bumpers":    suite_bumpers_triggers,
    "sticks":     suite_sticks,
    "combos":     suite_combos,
    "long_press": suite_long_press,
    "sequences":  suite_sequences,
}


# ══════════════════════════════════════════════════════════════════════════════
# Controller factory (reads hardware_config.yaml)
# ══════════════════════════════════════════════════════════════════════════════

def _build_controller(console: int) -> GimxController:
    """Build a GimxController from hardware_config.yaml."""
    from Automation_V4_Agent.config.loader import get_hw_config
    gimx = get_hw_config().get("gimx", {})
    key  = "controller_1" if console == 1 else "controller_2"
    c    = gimx.get(key, {})
    cfg  = GimxConfig(
        host            = c.get("host",        "127.0.0.1"),
        port            = c.get("port",         51914 if console == 1 else 51915),
        com_port        = c.get("com_port",     "COM8"),
        config_file     = c.get("config_file",  "XOnePadUsb.xml"),
        short_press_ms  = gimx.get("short_press_time_ms",   110),
        long_press_ms   = gimx.get("long_press_time_ms",   1500),
        cooldown_ms     = gimx.get("key_press_cooldown_ms",  220),
        post_press_delay_ms = gimx.get("post_press_delay_ms", 1000),
    )
    log.info(f"GimxController console={console}: {cfg.host}:{cfg.port}  "
             f"COM={cfg.com_port}  short={cfg.short_press_ms}ms  cooldown={cfg.cooldown_ms}ms")
    return GimxController(cfg)


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Xbox Controller Navigation Test — no image verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python Automation_V4_Agent/tests/controller_test.py
  python Automation_V4_Agent/tests/controller_test.py --suite dpad face
  python Automation_V4_Agent/tests/controller_test.py --suite sequences --console 2
  python Automation_V4_Agent/tests/controller_test.py --dry-run
  python Automation_V4_Agent/tests/controller_test.py --list-suites
        """,
    )
    parser.add_argument("--console", type=int, default=1, choices=[1, 2],
                        help="Xbox console controller to use (default: 1)")
    parser.add_argument("--suite", nargs="+", metavar="SUITE", default=["all"],
                        help="Test suite(s): all dpad face system bumpers sticks combos long_press sequences")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate steps without sending any controller input")
    parser.add_argument("--list-suites", action="store_true",
                        help="List available test suites and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_suites:
        print("\nAvailable test suites:")
        for name, fn in SUITE_MAP.items():
            doc = (fn.__doc__ or "").strip().split("\n")[0]
            print(f"  {name:<12}  {doc}")
        print(f"  {'all':<12}  Run every suite")
        return 0

    # Resolve suite list
    suites_to_run: list[str] = []
    for s in args.suite:
        if s == "all":
            suites_to_run = list(SUITE_MAP.keys())
            break
        if s in SUITE_MAP:
            suites_to_run.append(s)
        else:
            print(f"ERROR: Unknown suite '{s}'. Run --list-suites to see options.")
            return 1

    print(f"\n{'=' * 60}")
    print(f"  Xbox Controller Navigation Test")
    print(f"  Console : {args.console}")
    print(f"  Suites  : {', '.join(suites_to_run)}")
    print(f"  Dry run : {args.dry_run}")
    print(f"{'=' * 60}")

    if args.dry_run:
        print("  [DRY RUN] No UDP packets will be sent.\n")
        ctrl = None
    else:
        print("  Building controller... ", end="", flush=True)
        try:
            ctrl = _build_controller(args.console)
        except Exception as exc:
            print(f"FAILED\n  Error: {exc}")
            return 1

        print("OK")
        print("  Checking GIMX... ", end="", flush=True)
        alive = ctrl.check_status()
        if alive:
            print("GIMX already running — OK")
        else:
            print("GIMX not detected — attempting auto-start...")
            print(f"  Launching  : {ctrl.GIMX_EXECUTABLE}")
            print(f"  COM port   : {ctrl.config.com_port}")
            print(f"  Config     : {ctrl.config.config_file}")
            print("  Waiting up to 20s for GIMX to initialise... ", end="", flush=True)
            started = ctrl.start_gimx(wait_seconds=20)
            if started:
                print("OK — GIMX active")
            else:
                print("GIMX launched.")
                print()
                print("  NOTE: If GIMX console says:")
                print("  'Press the guide button of the controller for 2 seconds'")
                print("  — that is normal. The first button press from Python will")
                print("    register the controller with Xbox automatically.")
                print("  Ensure Leonardo USB is plugged into Xbox USB port.")
                print()

    runner = TestRunner(ctrl=ctrl, console=args.console, dry_run=args.dry_run)

    start = time.time()
    for suite_name in suites_to_run:
        SUITE_MAP[suite_name](runner)
    elapsed = time.time() - start

    print(f"\n  Total elapsed: {elapsed:.1f}s")
    return runner.summary()


if __name__ == "__main__":
    sys.exit(main())

