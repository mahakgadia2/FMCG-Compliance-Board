"""core/logger.py — thin helper around AnalysisContext.log for console + UI use."""
import sys


def print_log(context) -> None:
    """Dump the full pipeline log to stdout (useful for CLI / debugging)."""
    for line in context.log:
        print(line, file=sys.stdout)


def tail_log(context, n: int = 10):
    """Return the last n log lines — used by the Streamlit live panel."""
    return context.log[-n:]
