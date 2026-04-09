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
    def test_dashboard_renders_active_downloads_and_hides_done_items(self, write):
        out = output.TerminalOutput()

        out.dashboard_enqueue(1, "https://example.org/file.jpg")
        out.dashboard_start(1, "https://example.org/file.jpg", "file.jpg")
        out.dashboard_progress(1, 100, 50, 25)
        out.dashboard_issue(1, "network hiccup")
        retry_render = write.call_args_list[-1].args[0]
        out.dashboard_success(1, "file.jpg")
        final_render = write.call_args_list[-1].args[0]

        self.assertIn("active: 1  done: 0  skipped: 0  failed: 0", retry_render)
        self.assertIn(" 50% [████████░░░░░░░░] file.jpg (retrying)", retry_render)
        self.assertIn("https://example.org/file.jpg", retry_render)

        self.assertIn("active: 0  done: 1  skipped: 0  failed: 0", final_render)
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
        self.assertIn("active: 1  done: 0  skipped: 0  failed: 0", rendered)
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
        self.assertIn("active: 1  done: 5  skipped: 0  failed: 0", rendered)

    @patch("gallery_dl.output.stderr_write_flush")
    def test_dashboard_uses_color_output_styles(self, write):
        out = output.ColorOutput()

        out.dashboard_enqueue(1, "https://example.org/file.jpg")
        out.dashboard_start(1, "https://example.org/file.jpg", "file.jpg")
        out.dashboard_progress(1, 100, 50, 25)

        rendered = write.call_args_list[-1].args[0]
        self.assertIn("\x1b[", rendered)
        self.assertIn("active", rendered)
        self.assertIn(" 50% [████████░░░░░░░░] file.jpg", rendered)


if __name__ == "__main__":
    unittest.main()
