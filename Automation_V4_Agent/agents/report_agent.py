"""LangChain tool wrappers for test report generation (python-docx)."""
from __future__ import annotations
from langchain.tools import tool
from ..reporting.report_generator import ReportGenerator
from ..utils.logger import get_logger

log = get_logger("report_agent")

_report_gen: ReportGenerator | None = None


def _get_report_gen() -> ReportGenerator:
    global _report_gen
    if _report_gen is None:
        from ..config.loader import get_game_config
        cfg = get_game_config()
        r = cfg.get("report", {})
        _report_gen = ReportGenerator(
            output_dir=r.get("output_dir", "reports"),
            template_path=r.get("template_path", None),
        )
    return _report_gen


class ReportAgent:
    """Wraps ReportGenerator for LangChain tool interface."""

    def log_result(self, game_name: str, test_case: str, status: str,
                   latency_ms: float = 0.0, notes: str = "") -> bool:
        gen = _get_report_gen()
        gen.add_result(game_name, test_case, status, latency_ms, notes)
        log.info(f"Report: {game_name}/{test_case} = {status}")
        return True

    def save_report(self, filename: str | None = None) -> str:
        gen = _get_report_gen()
        return gen.save(filename)


def build_report_tools():
    """Return list of LangChain @tool functions for reporting."""
    agent = ReportAgent()

    @tool
    def log_test_result(game_name: str, test_case: str, status: str,
                        latency_ms: float = 0.0, notes: str = "") -> str:
        """Log a test result to the report.
        game_name: name of the game being tested.
        test_case: name of the specific test (e.g. 'Launch', 'Quit', 'SignIn').
        status: PASS or FAIL.
        latency_ms: measured latency in milliseconds (0 if not applicable).
        notes: optional free-text notes."""
        try:
            agent.log_result(game_name, test_case, status, latency_ms, notes)
            return f"OK: logged {game_name}/{test_case} = {status}"
        except Exception as exc:
            return f"ERROR: {exc}"

    @tool
    def save_test_report(filename: str = "") -> str:
        """Save the accumulated test results to a Word document (.docx).
        filename: optional output filename (auto-generated if empty)."""
        try:
            path = agent.save_report(filename or None)
            return f"OK: report saved to {path}"
        except Exception as exc:
            return f"ERROR: {exc}"

    return [log_test_result, save_test_report]
