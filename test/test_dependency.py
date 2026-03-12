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
from unittest.mock import Mock, patch

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOTDIR)
from gallery_dl import dependency  # noqa E402


class TestDependency(unittest.TestCase):

    @patch("gallery_dl.dependency.subprocess.run")
    @patch("gallery_dl.dependency.shutil.which")
    def test_ensure_aria2c_installs_with_package_manager(self, which, run):
        def which_side_effect(command):
            return {
                "aria2c": "/usr/bin/aria2c" if run.called else None,
                "sudo": None,
                "apt-get": "/usr/bin/apt-get",
            }.get(command)

        which.side_effect = which_side_effect
        run.return_value = Mock(returncode=0, stderr=b"")

        with patch("gallery_dl.dependency.util.WINDOWS", False), \
                patch("gallery_dl.dependency.os.geteuid", return_value=0):
            result = dependency.ensure_aria2c("aria2c")

        self.assertEqual(result, "/usr/bin/aria2c")
        run.assert_called_once_with(
            ["apt-get", "install", "-y", "aria2"],
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main()
