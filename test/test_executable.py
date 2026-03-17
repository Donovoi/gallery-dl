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
from pathlib import Path
from argparse import Namespace
from unittest.mock import call, patch

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = Path(ROOTDIR, ".github", "workflows", "executables.yml")
sys.path.insert(0, os.path.join(ROOTDIR, "scripts"))
import pyinstaller  # noqa E402


class TestExecutable(unittest.TestCase):

    def test_make_label_normalizes_ubuntu_x86(self):
        args = Namespace(
            os="ubuntu-latest",
            arch="x86",
            label=None,
            extension=None,
            print=False,
        )

        self.assertEqual(pyinstaller.make_label(args), "linux_x86")

    def test_make_label_appends_arm64_suffix(self):
        args = Namespace(
            os="ubuntu-24.04-arm",
            arch="aarch64",
            label=None,
            extension=None,
            print=False,
        )

        self.assertEqual(pyinstaller.make_label(args), "linux_arm64")

    @patch("pyinstaller.os.makedirs")
    def test_build_command_uses_nuitka_and_dist_output(self, makedirs):
        args = Namespace(
            os=None,
            arch=None,
            label="windows",
            extension="exe",
            print=False,
        )

        self.assertEqual(pyinstaller.build_command(args), [
            sys.executable,
            "-m", "nuitka",
            "--standalone",
            "--onefile",
            "--assume-yes-for-downloads",
            "--output-dir", os.path.join(ROOTDIR, "build"),
            "--output-filename", os.path.join(
                ROOTDIR, "dist", "gallery-dl_windows.exe"),
            os.path.join(ROOTDIR, "gallery_dl", "__main__.py"),
        ])
        makedirs.assert_not_called()

    @patch("pyinstaller.os.makedirs")
    @patch("pyinstaller.subprocess.call")
    def test_main_invokes_nuitka(self, subprocess_call, makedirs):
        subprocess_call.return_value = 0

        with patch.object(sys, "argv", ["pyinstaller.py", "--label", "linux"]):
            self.assertEqual(pyinstaller.main(), 0)

        self.assertEqual(makedirs.call_args_list, [
            call(os.path.join(ROOTDIR, "build"), exist_ok=True),
            call(os.path.join(ROOTDIR, "dist"), exist_ok=True),
        ])
        subprocess_call.assert_called_once_with([
            sys.executable,
            "-m", "nuitka",
            "--standalone",
            "--onefile",
            "--assume-yes-for-downloads",
            "--output-dir", os.path.join(ROOTDIR, "build"),
            "--output-filename", os.path.join(
                ROOTDIR, "dist", "gallery-dl_linux"),
            os.path.join(ROOTDIR, "gallery_dl", "__main__.py"),
        ])


class TestExecutableWorkflow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text().replace("\r\n", "\n")

    def test_workflow_has_daily_schedule(self):
        self.assertRegex(self.workflow, r"(?m)^\s*schedule:\s*$")
        self.assertRegex(
            self.workflow,
            (r"(?m)^\s*-\s+cron:\s*(?P<quote>['\"])"
             r"[^'\"]+ \* \* \*(?P=quote)\s*$"),
        )

    def test_workflow_has_nightly_release_tag(self):
        self.assertIn(
            'if [[ "${{ github.event_name }}" == "schedule" ]]; then',
            self.workflow,
        )
        self.assertIn('RELEASE_TAG=nightly-${DATE}', self.workflow)
        self.assertIn('RELEASE_TAG=master-${GITHUB_SHA}', self.workflow)


if __name__ == "__main__":
    unittest.main()
