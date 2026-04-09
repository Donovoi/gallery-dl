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
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gallery_dl import output, config  # noqa E402


class TestDashboardOutput(unittest.TestCase):

    def tearDown(self):
        config.clear()

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_renders_url_progress_and_issues(self, write):
        out = output.TerminalOutput()

        out.dashboard_enqueue(1, "https://example.org/file.jpg")
        out.dashboard_start(1, "https://example.org/file.jpg", "file.jpg")
        out.dashboard_progress(1, 100, 50, 25)
        out.dashboard_issue(1, "network hiccup")
        out.dashboard_success(1, "file.jpg")

        rendered = "".join(call.args[0] for call in write.call_args_list)
        self.assertIn("gallery-dl aria2c dashboard", rendered)
        self.assertIn("https://example.org/file.jpg", rendered)
        self.assertIn(" 50%", rendered)
        self.assertIn("B/s", rendered)
        self.assertIn("network hiccup", rendered)
        self.assertIn("[DONE]", rendered)

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
        self.assertIn("gallery-dl aria2c dashboard", rendered)
        self.assertNotIn("\x1b[2J", rendered)
        self.assertNotIn("\x1b[J", rendered)

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_prunes_completed_tasks(self, _write):
        out = output.TerminalOutput()

        for num in range(output.DASHBOARD_COMPLETED_TASK_LIMIT + 5):
            out.dashboard_enqueue(num, f"https://example.org/{num}.jpg")
            out.dashboard_success(num, f"{num}.jpg")

        out.dashboard_enqueue("active", "https://example.org/active.jpg")

        self.assertEqual(
            len(out._dashboard_tasks),
            output.DASHBOARD_COMPLETED_TASK_LIMIT + 1,
        )
        self.assertIn("active", out._dashboard_tasks)
        self.assertNotIn(0, out._dashboard_tasks)


if __name__ == "__main__":
    unittest.main()
