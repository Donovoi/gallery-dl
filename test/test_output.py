#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2026 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys
import unittest
import logging
import threading
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gallery_dl import output, config  # noqa E402


class TestDashboardOutput(unittest.TestCase):

    def tearDown(self):
        config.clear()

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_renders_active_downloads_and_hides_done_items(
        self,
        write,
    ):
        out = output.TerminalOutput()

        out.dashboard_enqueue(1, "https://example.org/file.jpg")
        out.dashboard_start(1, "https://example.org/file.jpg", "file.jpg")
        out.dashboard_progress(1, 100, 50, 25)
        out.dashboard_issue(1, "network hiccup")
        retry_render = write.call_args_list[-1].args[0]
        out.dashboard_success(1, "file.jpg")
        final_render = write.call_args_list[-1].args[0]

        self.assertIn(
            "active: 1",
            retry_render,
        )
        self.assertIn(
            "done: 0",
            retry_render,
        )
        self.assertIn(
            "skipped: 0",
            retry_render,
        )
        self.assertIn(
            "failed: 0",
            retry_render,
        )
        self.assertIn(
            "↻  50% [████████░░░░░░░░] file.jpg (retrying: network hiccup)",
            retry_render,
        )
        self.assertIn("https://example.org/file.jpg", retry_render)
        self.assertIn("network hiccup", retry_render)

        self.assertIn(
            "active: 0",
            final_render,
        )
        self.assertIn(
            "done: 1",
            final_render,
        )
        self.assertIn(
            "skipped: 0",
            final_render,
        )
        self.assertIn(
            "failed: 0",
            final_render,
        )
        self.assertNotIn("file.jpg", final_render)
        self.assertNotIn("https://example.org/file.jpg", final_render)
        self.assertNotIn("network hiccup", final_render)

    def test_shorten_string(self):
        self.assertEqual(output.shorten_string("short", 10), "short")

        shortened = output.shorten_string("https://example.org/file.jpg", 16)
        self.assertNotEqual(shortened, "https://example.org/file.jpg")
        self.assertLessEqual(len(shortened), 16)

    def test_shorten_string_eaw(self):
        self.assertEqual(output.shorten_string_eaw("あいう", 6), "あいう")

        shortened = output.shorten_string_eaw("あいうえお", 8)
        self.assertNotEqual(shortened, "あいうえお")
        self.assertLessEqual(len(shortened), len("あいうえお"))

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_render_without_ansi_clear_sequences(self, write):
        out = output.TerminalOutput()

        with patch("gallery_dl.output.ANSI", False), \
                patch("gallery_dl.output.TTY_STDERR", False):
            out.dashboard_enqueue(1, "https://example.org/file.jpg")

        rendered = "".join(call.args[0] for call in write.call_args_list)
        self.assertIn("active: 1", rendered)
        self.assertIn("done: 0", rendered)
        self.assertIn("skipped: 0", rendered)
        self.assertIn("failed: 0", rendered)
        self.assertNotIn("\x1b[2J", rendered)
        self.assertNotIn("\x1b[J", rendered)

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_removes_completed_tasks_and_keeps_counts(self, write):
        out = output.TerminalOutput()

        for num in range(5):
            out.dashboard_enqueue(num, f"https://example.org/{num}.jpg")
            out.dashboard_success(num, f"{num}.jpg")

        out.dashboard_enqueue("active", "https://example.org/active.jpg")
        rendered = write.call_args_list[-1].args[0]

        self.assertEqual(len(out._dashboard_tasks), 1)
        self.assertIn("active", out._dashboard_tasks)
        self.assertNotIn(0, out._dashboard_tasks)
        self.assertIn("active: 1", rendered)
        self.assertIn("done: 5", rendered)
        self.assertIn("skipped: 0", rendered)
        self.assertIn("failed: 0", rendered)

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_uses_color_output_styles(self, write):
        out = output.ColorOutput()

        out.dashboard_enqueue(1, "https://example.org/file.jpg")
        out.dashboard_start(1, "https://example.org/file.jpg", "file.jpg")
        out.dashboard_progress(1, 100, 50, 25)

        rendered = write.call_args_list[-1].args[0]
        self.assertIn("\x1b[", rendered)
        self.assertIn("active", rendered)
        self.assertIn("▶  50% [████████░░░░░░░░] file.jpg", rendered)

    @patch("gallery_dl.output.stderr_write_flush")
    @patch("gallery_dl.output.stdout_write")
    def test_dashboard_refreshes_after_skip_output(self, stdout_write, write):
        out = output.TerminalOutput()

        with patch("gallery_dl.output.ANSI", True), \
                patch("gallery_dl.output.TTY_STDERR", True):
            out.dashboard_enqueue(1, "https://example.org/file.jpg")
            write.reset_mock()
            out.skip("skipped.jpg")

        stdout_write.assert_called_once()
        write.assert_called_once()
        self.assertIn("active: 1", write.call_args.args[0])

    @patch("gallery_dl.output.stderr_write_flush")
    @patch("gallery_dl.output.stdout_write")
    def test_color_dashboard_refreshes_after_skip_and_success(
        self, stdout_write, write,
    ):
        out = output.ColorOutput()

        with patch("gallery_dl.output.ANSI", True), \
                patch("gallery_dl.output.TTY_STDERR", True):
            out.dashboard_enqueue(1, "https://example.org/file.jpg")
            write.reset_mock()
            out.skip("skipped.jpg")
            out.success("done.jpg")

        self.assertEqual(stdout_write.call_count, 2)
        self.assertEqual(write.call_count, 2)
        self.assertIn("active: 1", write.call_args.args[0])

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_refresh_uses_dashboard_lock(self, write):
        out = output.TerminalOutput()
        out._dashboard_used = True
        started = threading.Event()
        finished = threading.Event()

        with patch("gallery_dl.output.ANSI", True), \
                patch("gallery_dl.output.TTY_STDERR", True), \
                out._dashboard_lock:
            thread = threading.Thread(
                target=lambda: (
                    started.set(),
                    out._dashboard_refresh(),
                    finished.set(),
                ),
            )
            thread.start()
            started.wait(1)
            self.assertFalse(finished.wait(0.1))
            write.assert_not_called()

        thread.join(1)
        self.assertFalse(thread.is_alive())
        write.assert_called_once()

    def test_dashboard_log_handler_refreshes_active_dashboard(self):
        out = output.TerminalOutput()
        out._dashboard_used = True

        record = logging.LogRecord(
            "gallery-dl", logging.ERROR, __file__, 1, "boom", (), None
        )
        handler = output.DashboardStreamHandler(stream=sys.stderr)

        with patch("gallery_dl.output.ACTIVE_OUTPUT", out), \
                patch("gallery_dl.output.ANSI", True), \
                patch("gallery_dl.output.TTY_STDERR", True), \
                patch.object(out, "_dashboard_render") as render, \
                patch.object(logging.StreamHandler, "emit"):
            handler.emit(record)

        render.assert_called_once()


if __name__ == "__main__":
    unittest.main()
