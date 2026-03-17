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
from unittest.mock import Mock, call, patch

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

    @patch("gallery_dl.dependency._run_command")
    @patch("gallery_dl.dependency.importlib.util.find_spec")
    def test_install_python_package_bootstraps_missing_pip(
            self, find_spec, run_command):
        def find_spec_side_effect(name):
            if name == "pip":
                return None
            if name == "ensurepip":
                return object()
            return object()

        find_spec.side_effect = find_spec_side_effect
        run_command.side_effect = (True, True)

        result = dependency._install_python_package("yt-dlp")

        self.assertTrue(result)
        self.assertEqual(run_command.call_args_list, [
            call([
                sys.executable,
                "-m",
                "ensurepip",
                "--default-pip",
            ]),
            call([
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "yt-dlp",
            ]),
        ])

    @patch("gallery_dl.dependency._run_command")
    @patch("gallery_dl.dependency.importlib.util.find_spec")
    def test_install_python_package_requires_pip_or_ensurepip(
            self, find_spec, run_command):
        find_spec.return_value = None

        result = dependency._install_python_package("yt-dlp")

        self.assertFalse(result)
        run_command.assert_not_called()

    @patch("gallery_dl.dependency._announce")
    @patch("gallery_dl.dependency._install_python_package")
    @patch("gallery_dl.dependency._find_python_module")
    @patch("gallery_dl.dependency._install_system_package")
    @patch("gallery_dl.dependency.ensure_aria2c")
    @patch("gallery_dl.dependency._find_executable")
    def test_install_optional_dependencies_installs_missing_dependencies(
            self, find_executable, ensure_aria2c,
            install_system_package, find_python_module,
            install_python_package, announce):
        find_executable.return_value = None
        ensure_aria2c.return_value = "/usr/bin/aria2c"
        install_system_package.return_value = True
        find_python_module.return_value = None
        install_python_package.return_value = True

        with patch("gallery_dl.dependency.sys.platform", "linux"), \
                patch("gallery_dl.dependency.sys.version_info", (3, 10, 0)):
            result = dependency.install_optional_dependencies()

        self.assertTrue(result)
        ensure_aria2c.assert_called_once_with("aria2c")
        self.assertEqual(install_system_package.call_args_list, [
            call("ffmpeg"),
            call("mkvmerge"),
        ])
        self.assertEqual(install_python_package.call_args_list, [
            call("yt-dlp[default]"),
            call("requests[socks]"),
            call("brotli"),
            call("zstandard"),
            call("pyyaml"),
            call("toml"),
            call("secretstorage"),
            call("psycopg[binary]"),
            call("truststore"),
            call("jinja2"),
        ])
        announce.assert_any_call(
            "Installing optional dependencies listed in the README")
        announce.assert_any_call("Optional dependency installation finished")

    @patch("gallery_dl.dependency._announce")
    @patch("gallery_dl.dependency._install_python_package")
    @patch("gallery_dl.dependency._find_python_module")
    @patch("gallery_dl.dependency._install_system_package")
    @patch("gallery_dl.dependency.ensure_aria2c")
    @patch("gallery_dl.dependency._find_executable")
    def test_install_optional_dependencies_is_idempotent(
            self, find_executable, ensure_aria2c,
            install_system_package, find_python_module,
            install_python_package, announce):
        find_executable.return_value = "/usr/bin/tool"
        find_python_module.return_value = object()

        with patch("gallery_dl.dependency.sys.platform", "linux"), \
                patch("gallery_dl.dependency.sys.version_info", (3, 10, 0)):
            result = dependency.install_optional_dependencies()

        self.assertTrue(result)
        ensure_aria2c.assert_not_called()
        install_system_package.assert_not_called()
        install_python_package.assert_not_called()
        announce.assert_any_call("aria2c: already installed")
        announce.assert_any_call("Optional dependency installation finished")

    def test_is_aria2c_installed(self):
        self.assertTrue(dependency._is_aria2c_installed(
            "/usr/bin/aria2c", "aria2c"))
        self.assertFalse(dependency._is_aria2c_installed(
            "aria2c", "aria2c"))
        self.assertFalse(dependency._is_aria2c_installed(
            None, "aria2c"))


if __name__ == "__main__":
    unittest.main()
