"""
Xbox AI Agent Executor — ReAct agent powered by LiteLLM (GPT-4o / Claude Sonnet).

This module wires together:
  - LiteLLM-backed ChatLiteLLM (the "brain")
  - All hardware + vision + reporting LangChain tools (the "hands")
  - A ReAct prompt (the "reasoning loop")
  - LangChain AgentExecutor (the "orchestrator")

Usage:
    from Automation_V4_Agent.agents.agent_executor import build_xbox_agent

    agent = build_xbox_agent(console=1)
    result = agent.invoke({
        "input": "Launch Celeste, verify the main menu appears, then quit back to home."
    })
    print(result["output"])
"""
from __future__ import annotations

import time
from typing import Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.prompts import PromptTemplate

from .controller_agent import build_controller_tools
from .vision_agent import build_vision_tools
from .serial_agent import build_serial_tools
from .report_agent import build_report_tools
from .llm_factory import get_llm, get_fallback_llm, current_model_info
from ..config.loader import get_llm_config
from ..utils.logger import get_logger

log = get_logger("agent_executor")


# ─── ReAct Prompt Template ────────────────────────────────────────────────────

# Standard LangChain ReAct format — must include {tools}, {tool_names},
# {input}, and {agent_scratchpad} placeholders.
REACT_SYSTEM_PROMPT = """\
You are an expert Xbox console test automation engineer with access to hardware \
control tools. Your mission is to execute game test scenarios on real Xbox hardware.

HARDWARE TOOLS AVAILABLE:
- **Controller tools**: Press/hold Xbox buttons (A, B, X, Y, LB, RB, LT, RT, \
GUIDE, MENU, VIEW, UP, DOWN, LEFT, RIGHT, LS, RS). Move analog sticks.
- **Vision tools**: Capture screenshots, verify screen patterns via template \
matching, read on-screen text using OCR.
- **Serial tools**: Trigger relay board buttons, send keystrokes via Arduino KBM.
- **Report tools**: Log PASS/FAIL results, save the Word report.

TESTING METHODOLOGY:
1. Press the Xbox GUIDE button to go to Home
2. Navigate to the game tile and press A to launch
3. Wait for the game to load (verify with pattern matching)
4. Execute game-specific interactions
5. Verify each action with a screenshot + pattern match
6. Log each step as PASS or FAIL
7. Quit the game (hold GUIDE → navigate to Quit → A → A)
8. Verify you are back on the Xbox home screen

RULES:
- Always verify a screen BEFORE interacting with it
- If a verification fails, retry up to 2 times with a 2-second wait
- Never skip logging — every step must be logged
- If a step fails 3 times, log it as FAIL and move on
- Use short_press for normal navigation, long_press for Guide/power actions

TOOLS:
{tools}

Use the following format STRICTLY:

Question: the test scenario to execute
Thought: what I need to do next
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I have completed the test scenario
Final Answer: summary of all test results (PASS/FAIL per step)

Begin!

Question: {input}
Thought: {agent_scratchpad}"""


def _build_react_prompt() -> PromptTemplate:
    """Build the ReAct PromptTemplate, injecting system_role from llm_config.yaml."""
    cfg = get_llm_config()["llm"]
    # Optionally prepend the config system_role to the prompt
    system_role_extra = cfg.get("system_role", "").strip()
    full_prompt = REACT_SYSTEM_PROMPT
    if system_role_extra:
        full_prompt = system_role_extra + "\n\n" + REACT_SYSTEM_PROMPT

    return PromptTemplate.from_template(full_prompt)


# ─── Agent Builder ────────────────────────────────────────────────────────────

def build_xbox_agent(
    console: int = 1,
    model: Optional[str] = None,
    verbose: Optional[bool] = None,
) -> AgentExecutor:
    """
    Build and return a fully configured Xbox test AgentExecutor.

    The agent uses:
      - LiteLLM (GPT-4o or Claude) as the reasoning LLM
      - All 4 tool groups (controller, vision, serial, report)
      - ReAct reasoning loop
      - Automatic fallback to secondary model on LLM errors

    Args:
        console:  Which Xbox console (1 or 2) the controller tools target.
        model:    Override LLM model string (e.g. "gpt-4o"). Defaults to config.
        verbose:  Print LLM chain steps. Defaults to llm_config.yaml setting.

    Returns:
        Configured ``AgentExecutor`` ready to ``invoke({"input": "..."})``
    """
    cfg = get_llm_config()["llm"]

    # ── Gather all tools ──────────────────────────────────────────────────
    tools = (
        build_controller_tools(console)   # Xbox GIMX gamepad
        + build_vision_tools()            # Pattern match + OCR
        + build_serial_tools()            # Relay board + Arduino KBM
        + build_report_tools()            # Word doc reporting
    )

    log.info(f"Xbox agent: {len(tools)} tools loaded for console {console}")
    for t in tools:
        log.debug(f"  Tool: {t.name}")

    # ── LLM ──────────────────────────────────────────────────────────────
    llm = get_llm(model=model)
    info = current_model_info()
    log.info(f"LLM brain: {info['primary_model']} (provider={info['provider']})")

    # ── Prompt ───────────────────────────────────────────────────────────
    prompt = _build_react_prompt()

    # ── ReAct agent ──────────────────────────────────────────────────────
    react_agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    # ── Executor settings ────────────────────────────────────────────────
    is_verbose = verbose if verbose is not None else cfg.get("agent_verbose", True)
    max_iter = cfg.get("agent_max_iterations", 25)
    handle_parse = cfg.get("agent_handle_parse_errors", True)

    executor = AgentExecutor(
        agent=react_agent,
        tools=tools,
        verbose=is_verbose,
        max_iterations=max_iter,
        handle_parsing_errors=handle_parse,
        return_intermediate_steps=True,   # capture each tool call for reporting
        early_stopping_method="generate",
    )

    log.info(f"AgentExecutor ready: max_iterations={max_iter}  verbose={is_verbose}")
    return executor


def run_game_test_with_agent(
    game_name: str,
    console: int = 1,
    model: Optional[str] = None,
) -> dict:
    """
    High-level helper: run a complete game test using the AI agent.

    The agent receives a natural-language task description and autonomously
    decides which tools to call, in what order, with what parameters.

    Args:
        game_name: Name of the game to test (e.g. "Celeste", "Gears 5").
        console:   Which Xbox console (1 or 2).
        model:     Optional LLM model override.

    Returns:
        dict with keys:
          - "output"              : agent's final answer (summary)
          - "intermediate_steps" : list of (AgentAction, tool_output) tuples
          - "success"            : bool — True if agent completed without error
          - "duration_seconds"   : float — wall-clock time taken
    """
    agent = build_xbox_agent(console=console, model=model)

    task = (
        f"Execute the full test lifecycle for the game '{game_name}' on console {console}:\n"
        f"1. Navigate to the Xbox home screen (press GUIDE button)\n"
        f"2. Find and launch '{game_name}' from the game library\n"
        f"3. Wait for the game to fully load — verify with pattern matching\n"
        f"4. Navigate through the main menu to confirm the game is functional\n"
        f"5. Quit the game back to the Xbox home screen\n"
        f"6. Log a PASS result if all steps succeed, or FAIL with notes if any step fails\n"
        f"7. Save the test report\n"
        f"Provide a final summary of PASS/FAIL for each step."
    )

    log.info(f"Agent starting: game={game_name}  console={console}")
    start = time.time()
    success = True

    try:
        result = agent.invoke({"input": task})
    except Exception as exc:
        log.error(f"Agent failed for {game_name}: {exc}")
        log.info("Retrying with fallback LLM…")
        try:
            fallback_llm = get_fallback_llm()
            prompt = _build_react_prompt()
            tools = (
                build_controller_tools(console)
                + build_vision_tools()
                + build_serial_tools()
                + build_report_tools()
            )
            cfg = get_llm_config()["llm"]
            fallback_agent = AgentExecutor(
                agent=create_react_agent(fallback_llm, tools, prompt),
                tools=tools,
                verbose=cfg.get("agent_verbose", True),
                max_iterations=cfg.get("agent_max_iterations", 25),
                handle_parsing_errors=True,
                return_intermediate_steps=True,
            )
            result = fallback_agent.invoke({"input": task})
        except Exception as exc2:
            log.error(f"Fallback agent also failed: {exc2}")
            success = False
            result = {
                "output": f"ERROR: Both primary and fallback LLM failed. {exc2}",
                "intermediate_steps": [],
            }

    duration = time.time() - start
    log.info(f"Agent completed in {duration:.1f}s — success={success}")

    return {
        "output": result.get("output", ""),
        "intermediate_steps": result.get("intermediate_steps", []),
        "success": success,
        "duration_seconds": duration,
    }
