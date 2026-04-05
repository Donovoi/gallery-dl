#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2026 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import re
import unittest
from pathlib import Path

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = Path(ROOTDIR, ".github", "workflows", "sync-fork.yml")


class TestSyncForkWorkflow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text().replace("\r\n", "\n")
        cls.lines = cls.workflow.splitlines()

    def test_workflow_has_dispatch_and_scheduled_triggers(self):
        self.assertIn("  workflow_dispatch:", self.lines)
        self.assertIn("  repository_dispatch:", self.lines)
        self.assertIn("    types:", self.lines)
        self.assertIn("      - upstream_master_push", self.lines)
        self.assertRegex(
            self.workflow,
            r'(?m)^\s+- cron: (?P<quote>[\'"])17 \* \* \* \*(?P=quote)$',
        )

    def test_workflow_uses_write_permissions(self):
        self.assertIn("permissions:", self.lines)
        self.assertIn("  contents: write", self.lines)

    def test_workflow_runs_only_in_fork(self):
        self.assertIn(
            "if: github.repository == 'Donovoi/gallery-dl'",
            self.workflow,
        )

    def test_workflow_checks_out_master_with_full_history(self):
        match = re.search(
            (r"(?ms)- uses: actions/checkout@v5\n"
             r"\s+with:\n(?P<body>(?:\s+.+\n)+)"),
            self.workflow,
        )
        self.assertIsNotNone(match)
        self.assertRegex(match.group("body"), r"(?m)^\s+ref: master$")
        self.assertRegex(match.group("body"), r"(?m)^\s+fetch-depth: 0$")

    def test_workflow_fetches_and_merges_upstream_master(self):
        self.assertIn(
            "git remote add upstream https://github.com/mikf/gallery-dl.git",
            self.workflow,
        )
        self.assertIn("git fetch upstream master", self.workflow)
        self.assertIn("git merge --ff-only upstream/master", self.workflow)
        self.assertIn(
            "git merge -X theirs --no-commit upstream/master",
            self.workflow,
        )
        self.assertIn("git push origin HEAD:master", self.workflow)

    def test_workflow_resolves_conflicts_in_favor_of_upstream(self):
        self.assertIn(
            'echo "::error::Automatic merge with upstream/master failed"',
            self.workflow,
        )
        self.assertIn(
            "git diff --name-only --diff-filter=U",
            self.workflow,
        )
        self.assertIn(
            'if git show ":3:$path" >/dev/null 2>&1; then',
            self.workflow,
        )
        self.assertIn(
            'git checkout --theirs -- "$path"',
            self.workflow,
        )
        self.assertIn(
            'git rm -f -- "$path"',
            self.workflow,
        )
        self.assertIn("git commit --no-edit", self.workflow)


if __name__ == "__main__":
    unittest.main()
