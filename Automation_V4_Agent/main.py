#!/usr/bin/env python3
"""
Automation V4 Agent — Main Entry Point
Replaces: Automation V3/Sources/Script/TestCase/MainUser.ps1

Usage:
    python main.py                          # Run all games (console 1)
    python main.py --games Celeste Gears5   # Run specific games
    python main.py --console 2              # Use console 2 controller
    python main.py --list                   # List available games
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Ensure package root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from Automation_V4_Agent.utils.logger import setup_logging, get_logger
from Automation_V4_Agent.graphs.test_execution_graph import build_test_execution_graph, TestState

setup_logging(log_dir="logs")
log = get_logger("main")

# -- All 19 games from V3 MainUser.ps1 ---
ALL_GAMES = [
    "Celeste",
    "Gears 5",
    "Hollow Knight",
    "Sea of Stars",
    "Ori and the Will of the Wisps",
    "Halo Infinite",
    "Forza Horizon 5",
    "Minecraft Dungeons",
    "Psychonauts 2",
    "Outer Wilds",
    "Cuphead",
    "The Artful Escape",
    "Unpacking",
    "Tunic",
    "Pentiment",
    "Hi-Fi Rush",
    "Lies of P",
    "Starfield",
    "Forza Motorsport",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Xbox Automation V4 Agent — LiteLLM-powered test orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Run all 19 games with GPT-4o
  python main.py --games Celeste "Gears 5"          # Run specific games
  python main.py --model claude-3-5-sonnet-20241022 # Use Claude instead of GPT-4o
  python main.py --console 2                        # Target console 2
  python main.py --list                             # Show all available games
        """,
    )
    parser.add_argument("--games", nargs="+", metavar="GAME",
                        help="Space-separated list of game names to test")
    parser.add_argument("--console", type=int, default=1, choices=[1, 2],
                        help="Xbox console to test (1 or 2, default: 1)")
    parser.add_argument("--model", type=str, default=None, metavar="MODEL",
                        help=(
                            "LiteLLM model to use as AI brain. "
                            "Examples: gpt-4o, gpt-4-turbo, claude-3-5-sonnet-20241022. "
                            "Overrides llm_config.yaml and LITELLM_MODEL env var."
                        ))
    parser.add_argument("--max-retries", type=int, default=2,
                        help="Max retries per game on failure (default: 2)")
    parser.add_argument("--list", action="store_true",
                        help="List all available games and exit")
    parser.add_argument("--model-info", action="store_true",
                        help="Show current LLM configuration and exit")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list:
        print("Available games:")
        for i, g in enumerate(ALL_GAMES, 1):
            print(f"  {i:2}. {g}")
        return

    if args.model_info:
        from Automation_V4_Agent.agents.llm_factory import current_model_info
        info = current_model_info()
        print("\n🧠 LLM Configuration:")
        print(f"  Primary model  : {info['primary_model']}")
        print(f"  Fallback model : {info['fallback_model']}")
        print(f"  Provider       : {info['provider']}")
        print(f"  Temperature    : {info['temperature']}")
        print(f"  Max tokens     : {info['max_tokens']}")
        print("\nTo switch models:")
        print("  --model gpt-4o")
        print("  --model claude-3-5-sonnet-20241022")
        print("  set LITELLM_MODEL=gpt-4o-mini")
        return

    games = args.games if args.games else ALL_GAMES
    model_label = args.model or "config-default"
    log.info(
        f"Starting Automation V4 — {len(games)} game(s) on Console {args.console} "
        f"| 🧠 LLM: {model_label}"
    )

    # Build initial state (includes new agent_model + agent_outputs fields)
    initial_state: TestState = {
        "games_to_test": games,
        "console": args.console,
        "agent_model": args.model,       # None = use llm_config.yaml default
        "current_game": "",
        "current_step": "init",
        "games_completed": [],
        "games_failed": [],
        "results": [],
        "agent_outputs": [],             # populated by node_ai_run_tests
        "retry_count": 0,
        "max_retries": args.max_retries,
        "error_message": None,
        "report_path": None,
    }

    # Build and run the LangGraph
    graph = build_test_execution_graph()
    log.info("LangGraph compiled — starting AI-powered execution…")

    final_state = graph.invoke(initial_state)

    # Summary
    completed = final_state.get("games_completed", [])
    failed = final_state.get("games_failed", [])
    total = len(completed) + len(failed)
    pass_rate = (len(completed) / total * 100) if total > 0 else 0.0

    log.info("=" * 60)
    log.info(f"COMPLETED  : {completed}")
    log.info(f"FAILED     : {failed}")
    log.info(f"PASS RATE  : {pass_rate:.1f}% ({len(completed)}/{total})")
    log.info(f"REPORT     : {final_state.get('report_path', 'N/A')}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()