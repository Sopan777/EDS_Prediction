"""
services/audit/terminal_logger.py
=================================
ANSI Color-Coded Terminal Logging for Dhatu Bodh (Spectral Lab - MaterialID).
Provides:
  - Windows VT100 ANSI escape sequence activation
  - ColoredFormatter for Python/Django standard logging (`django.server`, `django.request`, `dhatu_bodh`)
  - ColoredRequestLoggingMiddleware for HTTP request/response timing and status colorization
  - Helper functions for rich, structured rule-engine & knowledge-base terminal output
"""

import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional


def _enable_windows_ansi() -> None:
    """Enable native ANSI escape sequences in Windows PowerShell / CMD consoles."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11, STD_ERROR_HANDLE = -12
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            for handle_id in (-11, -12):
                handle = kernel32.GetStdHandle(handle_id)
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


_enable_windows_ansi()


class ANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors (bright / high-contrast for dark & light terminals)
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # Background badges
    BG_BLUE = "\033[44;97;1m"
    BG_GREEN = "\033[42;30;1m"
    BG_YELLOW = "\033[43;30;1m"
    BG_RED = "\033[41;97;1m"
    BG_MAGENTA = "\033[45;97;1m"
    BG_CYAN = "\033[46;30;1m"


LEVEL_COLORS = {
    "DEBUG": ANSI.GRAY,
    "INFO": ANSI.CYAN,
    "WARNING": ANSI.YELLOW,
    "ERROR": ANSI.RED,
    "CRITICAL": ANSI.BG_RED,
}

METHOD_COLORS = {
    "GET": ANSI.CYAN,
    "POST": ANSI.GREEN,
    "PUT": ANSI.YELLOW,
    "PATCH": ANSI.YELLOW,
    "DELETE": ANSI.RED,
}


def _status_color(status_code: int) -> str:
    if 200 <= status_code < 300:
        return ANSI.GREEN
    if 300 <= status_code < 400:
        return ANSI.CYAN
    if 400 <= status_code < 500:
        return ANSI.YELLOW
    return ANSI.RED


class ColoredFormatter(logging.Formatter):
    """
    Custom logging.Formatter that adds ANSI colors to timestamps, log levels,
    logger names, and Django runserver status lines.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_name = record.levelname
        lvl_color = LEVEL_COLORS.get(level_name, ANSI.WHITE)
        msg = record.getMessage()

        # Colorize standard django.server output if present
        status_code = getattr(record, "status_code", None)
        if record.name == "django.server":
            if status_code:
                try:
                    sc = int(status_code)
                    sc_col = _status_color(sc)
                    msg = f"{sc_col}{msg}{ANSI.RESET}"
                except Exception:
                    pass
            elif '"GET ' in msg or '"POST ' in msg or '"PUT ' in msg or '"DELETE ' in msg:
                for method, m_col in METHOD_COLORS.items():
                    token = f'"{method} '
                    if token in msg:
                        msg = msg.replace(token, f'"{m_col}{ANSI.BOLD}{method}{ANSI.RESET} ')
                        break

        prefix = (
            f"{ANSI.GRAY}[{ts}]{ANSI.RESET} "
            f"{lvl_color}{ANSI.BOLD}{level_name:<7}{ANSI.RESET} "
            f"{ANSI.MAGENTA}[{record.name}]{ANSI.RESET}"
        )

        formatted = f"{prefix} {msg}"
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            formatted += f"\n{ANSI.RED}{exc_text}{ANSI.RESET}"
        return formatted


def get_terminal_logger(name: str = "dhatu_bodh") -> logging.Logger:
    return logging.getLogger(name)


def log_prediction_summary(
    analysis_id: str,
    decision: str,
    family_code: str,
    family_name: str,
    confidence: int,
    top_component: str,
    indirect_family: str,
    indirect_source: str,
    indirect_decision: str,
    spectra_count: int,
    elapsed_s: float,
) -> None:
    """Print a rich color-coded summary box to the terminal whenever an EDS prediction runs."""
    logger = get_terminal_logger("dhatu_bodh.engine")

    dec_upper = str(decision).upper()
    if dec_upper == "IDENTIFIED":
        dec_badge = f"{ANSI.BG_GREEN} IDENTIFIED {ANSI.RESET}"
    elif dec_upper == "AMBIGUOUS":
        dec_badge = f"{ANSI.BG_YELLOW} AMBIGUOUS {ANSI.RESET}"
    else:
        dec_badge = f"{ANSI.BG_RED} {dec_upper} {ANSI.RESET}"

    ind_upper = str(indirect_decision).upper()
    if ind_upper == "IDENTIFIED":
        ind_col = ANSI.GREEN
    elif ind_upper == "AMBIGUOUS":
        ind_col = ANSI.YELLOW
    else:
        ind_col = ANSI.RED

    line = (
        f"{ANSI.BG_BLUE} EDS PREDICTION {ANSI.RESET} "
        f"{ANSI.CYAN}{ANSI.BOLD}{analysis_id}{ANSI.RESET} "
        f"({spectra_count} spec, {elapsed_s * 1000:.1f}ms) | "
        f"Direct: {dec_badge} {ANSI.BOLD}{ANSI.WHITE}[{family_code}] {family_name}{ANSI.RESET} "
        f"({ANSI.GREEN}{confidence}%{ANSI.RESET}) -> "
        f"Comp: {ANSI.CYAN}{ANSI.BOLD}{top_component}{ANSI.RESET} | "
        f"Indirect: {ind_col}{ANSI.BOLD}[{indirect_family}] {indirect_source}{ANSI.RESET}"
    )
    logger.info(line)


def log_kb_customization(
    target_type: str,
    identifier: str,
    summary: str,
) -> None:
    """Print a color-coded terminal message when Knowledge Base data is customized."""
    logger = get_terminal_logger("dhatu_bodh.kb")
    logger.info(
        f"{ANSI.BG_MAGENTA} KB CUSTOMIZED {ANSI.RESET} "
        f"{ANSI.YELLOW}{ANSI.BOLD}{target_type}{ANSI.RESET} "
        f"{ANSI.CYAN}[{identifier}]{ANSI.RESET} — {ANSI.WHITE}{summary}{ANSI.RESET}"
    )


class ColoredRequestLoggingMiddleware:
    """
    Logs every HTTP request with color-coded method, path, status code, and execution time in ms.
    Skips noisy static file requests unless they error.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = get_terminal_logger("dhatu_bodh.http")

    def __call__(self, request):
        t0 = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        path = request.get_full_path()
        status_code = getattr(response, "status_code", 200)

        # Skip routine static assets if 200/304 to keep terminal clean
        if path.startswith("/static/") and status_code < 400:
            return response

        method = request.method.upper()
        m_col = METHOD_COLORS.get(method, ANSI.WHITE)
        s_col = _status_color(status_code)

        if elapsed_ms < 100:
            t_col = ANSI.GREEN
        elif elapsed_ms < 500:
            t_col = ANSI.YELLOW
        else:
            t_col = ANSI.RED

        self.logger.info(
            f"{m_col}{ANSI.BOLD}{method:<6}{ANSI.RESET} "
            f"{ANSI.WHITE}{path:<42}{ANSI.RESET} "
            f"{s_col}{ANSI.BOLD}{status_code}{ANSI.RESET} "
            f"{t_col}({elapsed_ms:.1f}ms){ANSI.RESET}"
        )
        return response
