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

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOTDIR)
from gallery_dl import option  # noqa E402


class TestOption(unittest.TestCase):

    def test_help_mentions_aria2c_option(self):
        help_text = " ".join(option.build_parser().format_help().split())

        self.assertIn("-o downloader.http.aria2c=true", help_text)
        self.assertIn(
            "-o downloader.http.aria2c=/usr/local/bin/aria2c",
            help_text,
        )
        self.assertIn("--install-deps", help_text)

    @patch("gallery_dl.option.dependency.install_optional_dependencies")
    def test_install_deps_exits_after_install(self, install_optional_dependencies):
        install_optional_dependencies.return_value = True

        with self.assertRaises(SystemExit) as exc:
            option.build_parser().parse_args(["--install-deps"])

        self.assertEqual(exc.exception.code, 0)
        install_optional_dependencies.assert_called_once_with()
