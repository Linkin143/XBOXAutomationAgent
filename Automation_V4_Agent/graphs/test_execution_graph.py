"""Main LangGraph StateGraph for Xbox test automation orchestration.

Architecture:
    initialize → select_next_game → launch_game → ai_run_tests → quit_game
                                                ↓ (fail)
                                         handle_failure → (retry or) log_report
    quit_game → log_report → select_next_game → … → finalize → END

The LLM brain (LiteLLM → GPT-4o / Claude Sonnet) is wired into node_ai_run_tests,
which invokes a full ReAct AgentExecutor with all hardware + vision + report tools.
"""
from __future__ import annotations
import time
from typing import TypedDict, Optional, List, Annotated
import operator

from langgraph.graph import StateGraph, END

from ..agents.agent_executor import run_game_test_with_agent
from ..agents.llm_factory import current_model_info
from ..utils.logger import get_logger
from ..utils.helpers import wait_ms

log = get_logger("test_execution_graph")


# --- State ---

class TestState(TypedDict):
    """Shared state passed between LangGraph nodes."""
    # Input
    games_to_test: List[str]
    console: int                    # 1 or 2
    agent_model: Optional[str]      # LiteLLM model override (None = use config default)
    # Progress
    current_game: str
    current_step: str               # "launch" | "test" | "quit" | "report"
    games_completed: Annotated[List[str], operator.add]
    games_failed: Annotated[List[str], operator.add]
    # Result accumulation
    results: Annotated[List[dict], operator.add]
    agent_outputs: Annotated[List[dict], operator.add]  # raw LLM agent outputs
    # Control
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    # Output
    report_path: Optional[str]


# --- Nodes ---

def node_initialize(state: TestState) -> TestState:
    """Set up initial state, log LLM brain info."""
    log.info("=== Xbox Automation V4 — Test Execution Graph starting ===")
    info = current_model_info()
    log.info(
        f"🧠 LLM Brain: {info['primary_model']} "
        f"(provider={info['provider']}, fallback={info['fallback_model']})"
    )
    log.info(f"Games to test ({len(state['games_to_test'])}): {state['games_to_test']}")
    return {
        **state,
        "current_step": "initialized",
        "retry_count": 0,
        "error_message": None,
        "agent_outputs": [],
    }


def node_select_next_game(state: TestState) -> TestState:
    """Pick the next game from the pending list."""
    completed = set(state.get("games_completed", []))
    failed = set(state.get("games_failed", []))
    done = completed | failed
    pending = [g for g in state["games_to_test"] if g not in done]

    if not pending:
        log.info("All games processed.")
        return {**state, "current_game": "", "current_step": "all_done"}

    next_game = pending[0]
    log.info(f"Next game: {next_game}")
    return {**state, "current_game": next_game, "current_step": "launch", "retry_count": 0}


def node_launch_game(state: TestState) -> TestState:
    """Launch the current game via GIMX controller."""
    game = state["current_game"]
    log.info(f"[{game}] Launching…")
    try:
        from ..game_scripts import get_game_instance
        instance = get_game_instance(game, console=state["console"])
        ok = instance.launch()
        if ok:
            return {**state, "current_step": "test", "error_message": None}
        else:
            return {**state, "current_step": "launch_failed",
                    "error_message": f"{game} launch returned False"}
    except Exception as exc:
        log.error(f"[{game}] Launch exception: {exc}")
        return {**state, "current_step": "launch_failed", "error_message": str(exc)}


def node_ai_run_tests(state: TestState) -> TestState:
    """
    🧠 AI-POWERED NODE: The LLM brain (LiteLLM) autonomously executes game tests.

    The ReAct AgentExecutor reasons step-by-step, calling hardware + vision tools:
      Thought → Action (press_xbox_button) → Observation (OK/FAIL)
      Thought → Action (verify_screen_pattern) → Observation (PASS/FAIL)
      Thought → Action (log_test_result) → Observation (OK)
      ...
      Final Answer: PASS/FAIL summary

    On failure, the agent retries internally (up to agent_max_iterations).
    If both primary and fallback LLM fail, marks as test_failed.
    """
    game = state["current_game"]
    model = state.get("agent_model")  # None = use llm_config.yaml default
    log.info(f"[{game}] 🧠 AI agent starting (model={model or 'config-default'})…")

    agent_result = run_game_test_with_agent(
        game_name=game,
        console=state["console"],
        model=model,
    )

    log.info(f"[{game}] Agent finished in {agent_result['duration_seconds']:.1f}s")
    log.info(f"[{game}] Agent output: {agent_result['output'][:200]}…")

    # Parse success from agent output
    output_lower = agent_result["output"].lower()
    is_success = agent_result["success"] and "fail" not in output_lower

    return {
        **state,
        "current_step": "quit" if is_success else "test_failed",
        "error_message": None if is_success else agent_result["output"],
        "agent_outputs": [{
            "game": game,
            "output": agent_result["output"],
            "success": agent_result["success"],
            "duration_seconds": agent_result["duration_seconds"],
            "steps_count": len(agent_result["intermediate_steps"]),
        }],
    }


def node_quit_game(state: TestState) -> TestState:
    """Quit the current game back to Xbox home."""
    game = state["current_game"]
    log.info(f"[{game}] Quitting…")
    try:
        from ..game_scripts import get_game_instance
        instance = get_game_instance(game, console=state["console"])
        ok = instance.quit_game()
        result = {
            "game": game,
            "launch": "PASS",
            "test": "PASS",
            "quit": "PASS" if ok else "FAIL",
        }
        return {
            **state,
            "current_step": "report",
            "results": [result],
            "games_completed": [game],
            "error_message": None,
        }
    except Exception as exc:
        log.error(f"[{game}] Quit exception: {exc}")
        return {**state, "current_step": "report", "error_message": str(exc),
                "games_failed": [game]}


def node_handle_failure(state: TestState) -> TestState:
    """Handle failures with retry logic."""
    game = state["current_game"]
    retry = state.get("retry_count", 0) + 1
    max_r = state.get("max_retries", 2)
    log.warning(f"[{game}] Failure (attempt {retry}/{max_r}): {state.get('error_message')}")
    if retry <= max_r:
        wait_ms(3000)
        return {**state, "retry_count": retry, "current_step": "launch"}
    else:
        log.error(f"[{game}] Max retries exceeded — marking FAIL.")
        result = {
            "game": game,
            "launch": "FAIL",
            "test": "FAIL",
            "quit": "FAIL",
            "error": state.get("error_message", ""),
        }
        return {**state, "current_step": "report", "results": [result],
                "games_failed": [game]}


def node_log_report(state: TestState) -> TestState:
    """Log the current game result to the report."""
    from ..reporting.report_generator import ReportGenerator
    gen = ReportGenerator()
    for r in state.get("results", []):
        if r.get("game") == state["current_game"]:
            status = "PASS" if r.get("test") == "PASS" else "FAIL"
            gen.add_result(r["game"], "Full Run", status, notes=r.get("error", ""))
    log.info(f"Result logged for {state['current_game']}")
    return {**state, "current_step": "select_next"}


def node_finalize(state: TestState) -> TestState:
    """Save the final Word report."""
    from ..reporting.report_generator import ReportGenerator
    gen = ReportGenerator()
    # Re-add all results
    for r in state.get("results", []):
        status = "PASS" if r.get("test") == "PASS" else "FAIL"
        gen.add_result(r["game"], "Full Run", status, notes=r.get("error", ""))
    path = gen.save()
    log.info(f"=== Test run complete. Report: {path} ===")
    log.info(f"Completed: {state.get('games_completed')}")
    log.info(f"Failed:    {state.get('games_failed')}")
    return {**state, "report_path": path, "current_step": "done"}


# --- Routing ---

def route_after_select(state: TestState) -> str:
    if state["current_step"] == "all_done":
        return "finalize"
    return "launch_game"


def route_after_launch(state: TestState) -> str:
    if state["current_step"] == "launch_failed":
        return "handle_failure"
    return "run_tests"


def route_after_tests(state: TestState) -> str:
    if state["current_step"] == "test_failed":
        return "handle_failure"
    return "quit_game"


def route_after_failure(state: TestState) -> str:
    if state["current_step"] == "launch":
        return "launch_game"
    return "log_report"


def route_after_report(state: TestState) -> str:
    return "select_next_game"


# --- Graph builder ---

def build_test_execution_graph():
    """
    Assemble and compile the main LangGraph StateGraph.

    Graph flow:
        initialize
            → select_next_game
                → launch_game ──(fail)──→ handle_failure ──(retry)──→ launch_game
                               ──(ok)──→ ai_run_tests ──(fail)──→ handle_failure
                                                       ──(ok)──→ quit_game
                                                                   → log_report
                                                                   → select_next_game
                                                                   → … (loop)
            → finalize → END
    """
    g = StateGraph(TestState)

    # ── Register nodes ───────────────────────────────────────────────────
    g.add_node("initialize",        node_initialize)
    g.add_node("select_next_game",  node_select_next_game)
    g.add_node("launch_game",       node_launch_game)
    g.add_node("ai_run_tests",      node_ai_run_tests)   # 🧠 LLM-powered node
    g.add_node("quit_game",         node_quit_game)
    g.add_node("handle_failure",    node_handle_failure)
    g.add_node("log_report",        node_log_report)
    g.add_node("finalize",          node_finalize)

    # ── Wire edges ───────────────────────────────────────────────────────
    g.set_entry_point("initialize")
    g.add_edge("initialize", "select_next_game")

    g.add_conditional_edges(
        "select_next_game", route_after_select,
        {"finalize": "finalize", "launch_game": "launch_game"},
    )
    g.add_conditional_edges(
        "launch_game", route_after_launch,
        {"handle_failure": "handle_failure", "run_tests": "ai_run_tests"},
    )
    g.add_conditional_edges(
        "ai_run_tests", route_after_tests,
        {"handle_failure": "handle_failure", "quit_game": "quit_game"},
    )
    g.add_edge("quit_game", "log_report")
    g.add_conditional_edges(
        "handle_failure", route_after_failure,
        {"launch_game": "launch_game", "log_report": "log_report"},
    )
    g.add_edge("log_report", "select_next_game")
    g.add_edge("finalize", END)

    return g.compile()
