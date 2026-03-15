#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
        self.assertIn(" 50%", rendered)
        self.assertIn("#####-----", rendered)
        self.assertIn("B/s", rendered)
        self.assertIn("network hiccup", rendered)
        self.assertIn("[DONE]", rendered)
        self.assertIn("RUN:1  DONE:0  SKIP:0  ERR:0", rendered)
        self.assertIn("RUN:0  DONE:1  SKIP:0  ERR:0", rendered)

    @patch("gallery_dl.output.stderr_write_flush")
    def test_color_dashboard_uses_ansi_and_unicode_progress(self, write):
        out = output.ColorOutput()

        out.dashboard_start(1, "https://example.org/file.jpg", "file.jpg")
        out.dashboard_progress(1, 100, 50, 25)

        rendered = "".join(call.args[0] for call in write.call_args_list)
        self.assertIn("\x1b[", rendered)
        self.assertIn("▶ 1", rendered)
        self.assertIn("█", rendered)
        self.assertIn("░", rendered)
        self.assertIn("[", rendered)
        self.assertIn("file.jpg", rendered)


if __name__ == "__main__":
    unittest.main()
