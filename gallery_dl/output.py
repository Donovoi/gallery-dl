# -*- coding: utf-8 -*-

# Copyright 2015-2025 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys
import shutil
import logging
import threading
import unicodedata
from . import config, util, formatter


# --------------------------------------------------------------------
# Globals

try:
    TTY_STDOUT = sys.stdout.isatty()
except Exception:
    TTY_STDOUT = False

try:
    TTY_STDERR = sys.stderr.isatty()
except Exception:
    TTY_STDERR = False

try:
    TTY_STDIN = sys.stdin.isatty()
except Exception:
    TTY_STDIN = False


COLORS_DEFAULT = {}
COLORS = not os.environ.get("NO_COLOR")
if COLORS:
    if TTY_STDOUT:
        COLORS_DEFAULT["success"] = "1;32"
        COLORS_DEFAULT["skip"] = "2"
    if TTY_STDERR:
        COLORS_DEFAULT["debug"] = "0;37"
        COLORS_DEFAULT["info"] = "1;37"
        COLORS_DEFAULT["warning"] = "1;33"
        COLORS_DEFAULT["error"] = "1;31"


if util.WINDOWS:
    ANSI = COLORS and os.environ.get("TERM") == "ANSI"
    OFFSET = 1
    CHAR_SKIP = "# "
    CHAR_SUCCESS = "* "
    CHAR_ELLIPSIES = "..."
else:
    ANSI = COLORS
    OFFSET = 0
    CHAR_SKIP = "# "
    CHAR_SUCCESS = "✔ "
    CHAR_ELLIPSIES = "…"


# --------------------------------------------------------------------
# Logging

LOG_FORMAT = "[{name}][{levelname}] {message}"
LOG_FORMAT_DATE = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = logging.INFO
LOG_LEVELS = ("debug", "info", "warning", "error")


class Logger(logging.Logger):
    """Custom Logger that includes extra info in log records"""

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None,
                   factory=logging._logRecordFactory):
        rv = factory(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra:
            rv.__dict__.update(extra)
        return rv


class LoggerAdapter():
    """Trimmed-down version of logging.LoggingAdapter"""
    __slots__ = ("logger", "extra")

    def __init__(self, logger, job):
        self.logger = logger
        self.extra = job._logger_extra

    def traceback(self, exc):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger._log(
                logging.DEBUG, "", None, exc_info=exc, extra=self.extra)

    def debug(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.DEBUG):
            kwargs["extra"] = self.extra
            self.logger._log(logging.DEBUG, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.INFO):
            kwargs["extra"] = self.extra
            self.logger._log(logging.INFO, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.WARNING):
            kwargs["extra"] = self.extra
            self.logger._log(logging.WARNING, msg, args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self.logger.isEnabledFor(logging.ERROR):
            kwargs["extra"] = self.extra
            self.logger._log(logging.ERROR, msg, args, **kwargs)


class PathfmtProxy():
    __slots__ = ("job",)

    def __init__(self, job):
        self.job = job

    def __getattribute__(self, name):
        pathfmt = object.__getattribute__(self, "job").pathfmt
        return getattr(pathfmt, name, None) if pathfmt else None

    def __str__(self):
        if pathfmt := object.__getattribute__(self, "job").pathfmt:
            return pathfmt.path or pathfmt.directory
        return ""


class KwdictProxy():
    __slots__ = ("job",)

    def __init__(self, job):
        self.job = job

    def __getattribute__(self, name):
        pathfmt = object.__getattribute__(self, "job").pathfmt
        return pathfmt.kwdict.get(name) if pathfmt else None


class Formatter(logging.Formatter):
    """Custom formatter that supports different formats per loglevel"""

    def __init__(self, fmt, datefmt):
        if isinstance(fmt, dict):
            for key in LOG_LEVELS:
                value = fmt[key] if key in fmt else LOG_FORMAT
                fmt[key] = (formatter.parse(value).format_map,
                            "{asctime" in value)
        else:
            if fmt == LOG_FORMAT:
                fmt = (fmt.format_map, False)
            else:
                fmt = (formatter.parse(fmt).format_map, "{asctime" in fmt)
            fmt = {"debug": fmt, "info": fmt, "warning": fmt, "error": fmt}

        self.formats = fmt
        self.datefmt = datefmt

    def format(self, record):
        record.message = record.getMessage()
        fmt, asctime = self.formats[record.levelname]
        if asctime:
            record.asctime = self.formatTime(record, self.datefmt)
        msg = fmt(record.__dict__)
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            msg = f"{msg}\n{record.exc_text}"
        if record.stack_info:
            msg = f"{msg}\n{record.stack_info}"
        return msg


class FileHandler(logging.StreamHandler):
    def __init__(self, path, mode, encoding, delay=True):
        self.path = path
        self.mode = mode
        self.errors = None
        self.encoding = encoding

        if delay:
            logging.Handler.__init__(self)
            self.stream = None
            self.emit = self.emit_delayed
        else:
            logging.StreamHandler.__init__(self, self._open())

    def close(self):
        with self.lock:
            try:
                if self.stream:
                    try:
                        self.flush()
                        self.stream.close()
                    finally:
                        self.stream = None
            finally:
                logging.StreamHandler.close(self)

    def _open(self):
        try:
            return open(self.path, self.mode,
                        encoding=self.encoding, errors=self.errors)
        except FileNotFoundError:
            os.makedirs(os.path.dirname(self.path))
            return open(self.path, self.mode,
                        encoding=self.encoding, errors=self.errors)

    def emit_delayed(self, record):
        if self.mode != "w" or not self._closed:
            self.stream = self._open()
        self.emit = logging.StreamHandler.emit.__get__(self)
        self.emit(record)


def initialize_logging(loglevel):
    """Setup basic logging functionality before configfiles have been loaded"""
    # convert levelnames to lowercase
    for level in (10, 20, 30, 40, 50):
        name = logging.getLevelName(level)
        logging.addLevelName(level, name.lower())

    # register custom Logging class
    logging.Logger.manager.setLoggerClass(Logger)

    # setup basic logging to stderr
    formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(loglevel)
    root = logging.getLogger()
    root.setLevel(logging.NOTSET)
    root.addHandler(handler)

    return logging.getLogger("gallery-dl")


def configure_logging(loglevel):
    root = logging.getLogger()
    minlevel = loglevel

    # stream logging handler
    handler = root.handlers[0]
    opts = config.interpolate(("output",), "log")

    colors = config.interpolate(("output",), "colors")
    if colors is None:
        colors = COLORS_DEFAULT
    if colors and not opts:
        opts = LOG_FORMAT

    if opts:
        if isinstance(opts, str):
            logfmt = opts
            opts = {}
        elif "format" in opts:
            logfmt = opts["format"]
        else:
            logfmt = LOG_FORMAT

        if not isinstance(logfmt, dict) and colors:
            ansifmt = "\033[{}m{}\033[0m".format
            lf = {}
            for level in LOG_LEVELS:
                c = colors.get(level)
                lf[level] = ansifmt(c, logfmt) if c else logfmt
            logfmt = lf

        handler.setFormatter(Formatter(
            logfmt, opts.get("format-date", LOG_FORMAT_DATE)))

        if "level" in opts and handler.level == LOG_LEVEL:
            handler.setLevel(opts["level"])

        if minlevel > handler.level:
            minlevel = handler.level

    # file logging handler
    if handler := setup_logging_handler("logfile", lvl=loglevel):
        root.addHandler(handler)
        if minlevel > handler.level:
            minlevel = handler.level

    root.setLevel(minlevel)


def setup_logging_handler(key, fmt=LOG_FORMAT, lvl=LOG_LEVEL, mode="w",
                          defer=False):
    """Setup a new logging handler"""
    opts = config.interpolate(("output",), key)
    if not opts:
        return None
    if not isinstance(opts, dict):
        opts = {"path": opts}

    path = opts.get("path")
    mode = opts.get("mode", mode)
    encoding = opts.get("encoding", "utf-8")
    delay = opts.get("defer", defer)
    try:
        path = util.expand_path(path)
        handler = FileHandler(path, mode, encoding, delay)
    except (OSError, ValueError) as exc:
        logging.getLogger("gallery-dl").warning(
            "%s: %s", key, exc)
        return None
    except TypeError as exc:
        logging.getLogger("gallery-dl").warning(
            "%s: missing or invalid path (%s)", key, exc)
        return None

    handler.setLevel(opts.get("level", lvl))
    handler.setFormatter(Formatter(
        opts.get("format", fmt),
        opts.get("format-date", LOG_FORMAT_DATE),
    ))
    return handler


# --------------------------------------------------------------------
# Utility functions

def stdout_write_flush(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def stderr_write_flush(s):
    sys.stderr.write(s)
    sys.stderr.flush()


if getattr(sys.stdout, "line_buffering", None):
    def stdout_write(s):
        sys.stdout.write(s)
else:
    stdout_write = stdout_write_flush


if getattr(sys.stderr, "line_buffering", None):
    def stderr_write(s):
        sys.stderr.write(s)
else:
    stderr_write = stderr_write_flush


def configure_standard_streams():
    for name in ("stdout", "stderr", "stdin"):
        stream = getattr(sys, name, None)
        if not stream:
            continue

        options = config.get(("output",), name)
        if not options:
            options = {"errors": "replace"}
        elif isinstance(options, str):
            options = {"errors": "replace", "encoding": options}
        elif not options.get("errors"):
            options["errors"] = "replace"

        stream.reconfigure(**options)


# --------------------------------------------------------------------
# Downloader output

def select():
    """Select a suitable output class"""
    mode = config.get(("output",), "mode")

    if mode is None or mode == "auto":
        try:
            if TTY_STDOUT:
                output = ColorOutput() if ANSI else TerminalOutput()
            else:
                output = PipeOutput()
        except Exception:
            output = PipeOutput()
    elif isinstance(mode, dict):
        output = CustomOutput(mode)
    elif not mode:
        output = NullOutput()
    else:
        output = {
            "default" : PipeOutput,
            "pipe"    : PipeOutput,
            "term"    : TerminalOutput,
            "terminal": TerminalOutput,
            "color"   : ColorOutput,
            "null"    : NullOutput,
        }[mode.lower()]()

    if not config.get(("output",), "skip", True):
        output.skip = util.identity
    return output


class NullOutput():

    def start(self, path):
        """Print a message indicating the start of a download"""

    def skip(self, path):
        """Print a message indicating that a download has been skipped"""

    def success(self, path):
        """Print a message indicating the completion of a download"""

    def progress(self, bytes_total, bytes_downloaded, bytes_per_second):
        """Display download progress"""

    def dashboard_enqueue(self, task_id, url, path=None):
        """Register a queued dashboard task"""

    def dashboard_start(self, task_id, url, path):
        """Register a running dashboard task"""

    def dashboard_progress(self, task_id, bytes_total,
                           bytes_downloaded, bytes_per_second):
        """Update dashboard progress"""

    def dashboard_issue(self, task_id, message, fatal=False):
        """Register a dashboard issue"""

    def dashboard_skip(self, task_id, path=None):
        """Register a skipped dashboard task"""

    def dashboard_success(self, task_id, path=None):
        """Register a completed dashboard task"""


class PipeOutput(NullOutput):

    def skip(self, path):
        stdout_write(f"{CHAR_SKIP}{path}\n")

    def success(self, path):
        stdout_write(f"{path}\n")


class TerminalOutput():
    _DASHBOARD_LABELS = {
        "queued" : "QUE",
        "running": "RUN",
        "retry"  : "TRY",
        "done"   : "DONE",
        "skip"   : "SKIP",
        "error"  : "ERR",
    }

    def __init__(self):
        if shorten := config.get(("output",), "shorten", True):
            func = shorten_string_eaw if shorten == "eaw" else shorten_string
            limit = shutil.get_terminal_size().columns - OFFSET
            sep = CHAR_ELLIPSIES
            self.shorten = lambda txt: func(txt, limit, sep)
        else:
            self.shorten = util.identity
        self._dashboard_lock = threading.Lock()
        self._dashboard_tasks = {}
        self._dashboard_issues = []

    def start(self, path):
        stdout_write_flush(self.shorten(f"  {path}"))

    def skip(self, path):
        stdout_write(f"{self.shorten(CHAR_SKIP + path)}\n")

    def success(self, path):
        stdout_write(f"\r{self.shorten(CHAR_SUCCESS + path)}\n")

    def progress(self, bytes_total, bytes_downloaded, bytes_per_second):
        bdl = util.format_value(bytes_downloaded)
        bps = util.format_value(bytes_per_second)
        if bytes_total is None:
            stderr_write(f"\r{bdl:>7}B {bps:>7}B/s ")
        else:
            stderr_write(f"\r{bytes_downloaded * 100 // bytes_total:>3}% "
                         f"{bdl:>7}B {bps:>7}B/s ")

    def dashboard_enqueue(self, task_id, url, path=None):
        with self._dashboard_lock:
            task = self._dashboard_tasks.setdefault(task_id, {
                "path": path or "",
                "url": url,
                "status": "queued",
                "bytes_total": None,
                "bytes_downloaded": 0,
                "bytes_per_second": 0,
                "issue": "",
            })
            task["url"] = url
            if path:
                task["path"] = path
            task["status"] = "queued"
            self._dashboard_render()

    def dashboard_start(self, task_id, url, path):
        with self._dashboard_lock:
            task = self._dashboard_tasks.setdefault(task_id, {
                "path": "",
                "url": url,
                "status": "queued",
                "bytes_total": None,
                "bytes_downloaded": 0,
                "bytes_per_second": 0,
                "issue": "",
            })
            task["url"] = url
            task["path"] = path
            task["status"] = "running"
            self._dashboard_render()

    def dashboard_progress(self, task_id, bytes_total,
                           bytes_downloaded, bytes_per_second):
        with self._dashboard_lock:
            if task := self._dashboard_tasks.get(task_id):
                task["bytes_total"] = bytes_total
                task["bytes_downloaded"] = bytes_downloaded
                task["bytes_per_second"] = bytes_per_second
                if task["status"] == "queued":
                    task["status"] = "running"
                self._dashboard_render()

    def dashboard_issue(self, task_id, message, fatal=False):
        with self._dashboard_lock:
            if task := self._dashboard_tasks.get(task_id):
                task["issue"] = message
                task["status"] = "error" if fatal else "retry"
                label = task["path"] or task["url"]
            else:
                label = str(task_id)
            self._dashboard_issues.append((label, message))
            self._dashboard_issues = self._dashboard_issues[-10:]
            self._dashboard_render()

    def dashboard_skip(self, task_id, path=None):
        with self._dashboard_lock:
            if task := self._dashboard_tasks.get(task_id):
                if path:
                    task["path"] = path
                task["status"] = "skip"
                self._dashboard_render()

    def dashboard_success(self, task_id, path=None):
        with self._dashboard_lock:
            if task := self._dashboard_tasks.get(task_id):
                if path:
                    task["path"] = path
                task["status"] = "done"
                self._dashboard_render()

    def _dashboard_summary(self, status, count):
        return f"{self._dashboard_label(status)}:{count}"

    def _dashboard_label(self, status):
        return self._DASHBOARD_LABELS.get(status, status[:3].upper())

    def _dashboard_downloaded(self, total, downloaded):
        return min(downloaded, total) if total else downloaded

    def _dashboard_filled(self, total, downloaded, width):
        if not total or not downloaded:
            return 0
        return min(width, max(1, downloaded * width // total))

    def _dashboard_unknown(self, width):
        return ("unknown" + "." * width)[:width]

    def _dashboard_bar(self, status, total, downloaded, width=10):
        if not total:
            return self._dashboard_unknown(width)
        downloaded = self._dashboard_downloaded(total, downloaded)
        filled = self._dashboard_filled(total, downloaded, width)
        return "#" * filled + "-" * (width - filled)

    def _dashboard_title(self, text):
        return text

    def _dashboard_percent(self, total, downloaded):
        if not total:
            return " n/a"
        downloaded = self._dashboard_downloaded(total, downloaded)
        return f"{downloaded * 100 // total:>3}%"

    def _dashboard_show_url(self, task, status):
        return (
            task["path"] and task["path"] != task["url"] and
            (status in ("queued", "retry", "error") or task["issue"])
        )

    def _dashboard_show_task(self, status):
        return status in ("queued", "running", "retry", "error")

    def _dashboard_render(self):
        active = done = failed = skipped = 0
        lines = [
            self._dashboard_title("gallery-dl aria2c dashboard"),
        ]

        for task in self._dashboard_tasks.values():
            status = task["status"]
            if status in ("queued", "running", "retry"):
                active += 1
            elif status == "done":
                done += 1
            elif status == "skip":
                skipped += 1
            elif status == "error":
                failed += 1

        lines.append(
            "  ".join((
                self._dashboard_summary("running", active),
                self._dashboard_summary("done", done),
                self._dashboard_summary("skip", skipped),
                self._dashboard_summary("error", failed),
            )))
        lines.append("")

        for task in self._dashboard_tasks.values():
            status = task["status"]
            if not self._dashboard_show_task(status):
                continue
            total = task["bytes_total"]
            downloaded = task["bytes_downloaded"]
            speed = util.format_value(task["bytes_per_second"])
            percent = self._dashboard_percent(total, downloaded)
            label = self._dashboard_label(status)
            bar = self._dashboard_bar(status, total, downloaded)
            target = task["path"] or task["url"]
            lines.append(
                self.shorten(
                    f"[{label}] {percent} {bar} {speed:>7}B/s {target}"))
            if self._dashboard_show_url(task, status):
                lines.append(self.shorten(f"      {task['url']}"))
            if task["issue"]:
                lines.append(self.shorten(f"      issue: {task['issue']}"))

        if self._dashboard_issues:
            lines.extend(("", "issues:"))
            for label, message in self._dashboard_issues[-5:]:
                lines.append(self.shorten(f"  - {label}: {message}"))

        stderr_write_flush("\x1b[2J\x1b[H" + "\n".join(lines) + "\x1b[J")


class ColorOutput(TerminalOutput):
    _DASHBOARD_SYMBOLS = {
        "queued" : "…",
        "running": "▶",
        "retry"  : "↻",
        "done"   : "✓",
        "skip"   : "↷",
        "error"  : "✕",
    }

    def __init__(self):
        TerminalOutput.__init__(self)

        colors = config.interpolate(("output",), "colors")
        if colors is None:
            colors = COLORS_DEFAULT

        self.color_skip = f"\x1b[{colors.get('skip', '2')}m"
        self.color_success = f"\r\x1b[{colors.get('success', '1;32')}m"
        self._dashboard_colors = {
            "title"  : colors.get("info", "1;37"),
            "queued" : colors.get("queued", "0;36"),
            "running": colors.get("running", "1;34"),
            "retry"  : colors.get("warning", "1;33"),
            "done"   : colors.get("success", "1;32"),
            "skip"   : colors.get("skip", "2"),
            "error"  : colors.get("error", "1;31"),
            "muted"  : colors.get("debug", "0;37"),
        }

    def start(self, path):
        stdout_write_flush(self.shorten(path))

    def skip(self, path):
        stdout_write(f"{self.color_skip}{self.shorten(path)}\x1b[0m\n")

    def success(self, path):
        stdout_write(f"{self.color_success}{self.shorten(path)}\x1b[0m\n")

    def _dashboard_color(self, key, text):
        color = self._dashboard_colors.get(key)
        return f"\x1b[{color}m{text}\x1b[0m" if color else text

    def _dashboard_summary(self, status, count):
        symbol = self._DASHBOARD_SYMBOLS.get(
            status, self._dashboard_label(status))
        return self._dashboard_color(status, f"{symbol} {count}")

    def _dashboard_label(self, status):
        return self._dashboard_color(
            status,
            self._DASHBOARD_SYMBOLS.get(
                status,
                self._DASHBOARD_LABELS.get(status, status[:3].upper()),
            ),
        )

    def _dashboard_bar(self, status, total, downloaded, width=10):
        if not total:
            return self._dashboard_color(
                "muted", self._dashboard_unknown(width))
        downloaded = self._dashboard_downloaded(total, downloaded)
        filled = self._dashboard_filled(total, downloaded, width)
        return (
            self._dashboard_color(status, "█" * filled) +
            self._dashboard_color("muted", "░" * (width - filled))
        )

    def _dashboard_title(self, text):
        return self._dashboard_color("title", text)


class CustomOutput():

    def __init__(self, options):

        fmt_skip = options.get("skip")
        fmt_start = options.get("start")
        fmt_success = options.get("success")
        off_skip = off_start = off_success = 0

        if isinstance(fmt_skip, list):
            off_skip, fmt_skip = fmt_skip
        if isinstance(fmt_start, list):
            off_start, fmt_start = fmt_start
        if isinstance(fmt_success, list):
            off_success, fmt_success = fmt_success

        if shorten := config.get(("output",), "shorten", True):
            func = shorten_string_eaw if shorten == "eaw" else shorten_string
            width = shutil.get_terminal_size().columns

            self._fmt_skip = self._make_func(
                func, fmt_skip, width - off_skip)
            self._fmt_start = self._make_func(
                func, fmt_start, width - off_start)
            self._fmt_success = self._make_func(
                func, fmt_success, width - off_success)
        else:
            self._fmt_skip = fmt_skip.format
            self._fmt_start = fmt_start.format
            self._fmt_success = fmt_success.format

        self._fmt_progress = (options.get("progress") or
                              "\r{0:>7}B {1:>7}B/s ").format
        self._fmt_progress_total = (options.get("progress-total") or
                                    "\r{3:>3}% {0:>7}B {1:>7}B/s ").format

    def _make_func(self, shorten, format_string, limit):
        fmt = format_string.format
        return lambda txt: fmt(shorten(txt, limit, CHAR_ELLIPSIES))

    def start(self, path):
        stdout_write_flush(self._fmt_start(path))

    def skip(self, path):
        stdout_write(self._fmt_skip(path))

    def success(self, path):
        stdout_write(self._fmt_success(path))

    def progress(self, bytes_total, bytes_downloaded, bytes_per_second):
        bdl = util.format_value(bytes_downloaded)
        bps = util.format_value(bytes_per_second)
        if bytes_total is None:
            stderr_write(self._fmt_progress(bdl, bps))
        else:
            stderr_write(self._fmt_progress_total(
                bdl, bps, util.format_value(bytes_total),
                bytes_downloaded * 100 // bytes_total))

    dashboard_enqueue = NullOutput.dashboard_enqueue
    dashboard_start = NullOutput.dashboard_start
    dashboard_progress = NullOutput.dashboard_progress
    dashboard_issue = NullOutput.dashboard_issue
    dashboard_skip = NullOutput.dashboard_skip
    dashboard_success = NullOutput.dashboard_success


class EAWCache(dict):

    def __missing__(self, key):
        width = self[key] = \
            2 if unicodedata.east_asian_width(key) in "WF" else 1
        return width


def shorten_string(txt, limit, sep="…"):
    """Limit width of 'txt'; assume all characters have a width of 1"""
    if len(txt) <= limit:
        return txt
    limit -= len(sep)
    return f"{txt[:limit // 2]}{sep}{txt[-((limit+1) // 2):]}"


def shorten_string_eaw(txt, limit, sep="…", cache=EAWCache()):
    """Limit width of 'txt'; check for east-asian characters with width > 1"""
    char_widths = [cache[c] for c in txt]
    text_width = sum(char_widths)

    if text_width <= limit:
        # no shortening required
        return txt

    limit -= len(sep)
    if text_width == len(txt):
        # all characters have a width of 1
        return f"{txt[:limit // 2]}{sep}{txt[-((limit+1) // 2):]}"

    # wide characters
    left = 0
    lwidth = limit // 2
    while True:
        lwidth -= char_widths[left]
        if lwidth < 0:
            break
        left += 1

    right = -1
    rwidth = (limit+1) // 2 + (lwidth + char_widths[left])
    while True:
        rwidth -= char_widths[right]
        if rwidth < 0:
            break
        right -= 1

    return f"{txt[:left]}{sep}{txt[right+1:]}"
