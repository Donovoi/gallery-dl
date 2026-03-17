#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2026 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import unittest
from pathlib import Path

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = Path(ROOTDIR, ".github", "workflows", "tests.yml")


class TestTestsWorkflow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text().replace("\r\n", "\n")
        cls.lines = cls.workflow.splitlines()

    def test_push_runs_on_master(self):
        self.assertIn("  push:", self.lines)
        self.assertIn("    - master", self.lines)

    def test_push_runs_on_copilot_branches(self):
        self.assertIn("    - 'copilot/**'", self.lines)

    def test_pull_requests_still_target_master(self):
        self.assertIn("  pull_request:", self.lines)
        self.assertEqual(self.lines.count("    - master"), 2)


if __name__ == "__main__":
    unittest.main()
