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

ROOTDIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
README = ROOTDIR / "README.rst"


class TestReadmeExecutables(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.readme = README.read_text().replace("\r\n", "\n")

    def test_nightly_builds_explain_termux_binary_error(self):
        self.assertRegex(
            self.readme,
            (r"(?s)Nightly Builds\n-+\n.*cannot execute: required file not "
             r"found.*gallery-dl_linux_arm64"),
        )

    def test_nightly_builds_include_termux_oneliner(self):
        self.assertRegex(
            self.readme,
            (r"python3 -m pip install --user "
             r'"gallery-dl @ '
             r"https://github\.com/Donovoi/gallery-dl/archive/refs/heads/"
             r'master\.zip" '
             r"&& python3 -m gallery_dl URL"),
        )


if __name__ == "__main__":
    unittest.main()
