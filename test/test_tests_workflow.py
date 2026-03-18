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

    def test_workflow_run_triggers_for_copilot_agent(self):
        self.assertIn("  workflow_run:", self.lines)
        self.assertIn("    workflows:", self.lines)
        self.assertIn("    - Copilot coding agent", self.lines)
        self.assertIn("    types:", self.lines)
        self.assertIn("    - completed", self.lines)
        self.assertIn(
            "github.event.workflow_run.conclusion == 'success'",
            self.workflow,
        )
        self.assertIn(
            "github.event.workflow_run.head_repository.full_name == "
            "github.repository",
            self.workflow,
        )
        self.assertIn(
            "startsWith(github.event.workflow_run.head_branch, 'copilot/')",
            self.workflow,
        )

    def test_permissions_are_read_only(self):
        self.assertIn("permissions:", self.lines)
        self.assertIn("  contents: read", self.lines)

    def test_workflow_run_checks_out_agent_head_sha(self):
        self.assertRegex(
            self.workflow,
            (r"ref:\s*\$\{\{\s*github\.event_name == 'workflow_run'"
             r"\s*&&\s*github\.event\.workflow_run\.head_sha"
             r"\s*\|\|\s*github\.sha\s*\}\}"),
        )

    def test_pull_requests_still_target_master(self):
        self.assertRegex(
            self.workflow,
            r"(?ms)^  pull_request:\n    branches:\n    - master$",
        )


if __name__ == "__main__":
    unittest.main()
