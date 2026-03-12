# -*- coding: utf-8 -*-

# Copyright 2026 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Helpers for bootstrapping optional runtime dependencies"""

import importlib
import io
import json
import logging
import os
import shutil
import site
import subprocess
import sys
import zipfile
from urllib.request import Request, urlopen

from . import cache, util

log = logging.getLogger("dependency")
ARIA2_RELEASE_API = "https://api.github.com/repos/aria2/aria2/releases/latest"
ARIA2_PACKAGE_MANAGERS = (
    ("apt-get", True, ("install", "-y", "aria2")),
    ("dnf"    , True, ("install", "-y", "aria2")),
    ("yum"    , True, ("install", "-y", "aria2")),
    ("pacman" , True, ("-S", "--noconfirm", "aria2")),
    ("zypper" , True, ("--non-interactive", "install", "aria2")),
    ("apk"    , True, ("add", "aria2")),
    ("brew"   , False, ("install", "aria2")),
)


def ensure_aria2c(command):
    """Return a usable aria2c executable path or *command* as fallback."""
    if not command:
        return command

    if path := _find_executable(command):
        return path

    log.info("Attempting to install missing aria2c dependency")

    if util.WINDOWS:
        if path := _install_aria2c_windows():
            return path
    else:
        if path := _install_aria2c_package():
            return path

    return command


def ensure_python_module(import_name, package_name):
    """Import *import_name*, installing *package_name* with pip if needed."""
    try:
        return importlib.import_module(import_name)
    except (ImportError, SyntaxError) as exc:
        original_exc = exc

    log.info("Attempting to install missing Python package '%s'", package_name)

    if not _install_python_package(package_name):
        raise original_exc

    importlib.invalidate_caches()
    return importlib.import_module(import_name)


def _find_executable(command):
    return shutil.which(command)


def _install_aria2c_package():
    sudo = shutil.which("sudo")
    needs_root = hasattr(os, "geteuid") and os.geteuid() != 0

    for manager, require_root, args in ARIA2_PACKAGE_MANAGERS:
        if not shutil.which(manager):
            continue

        cmd = [manager, *args]
        if require_root and needs_root:
            if not sudo:
                continue
            cmd = [sudo, "-n", *cmd]

        if _run_command(cmd):
            return _find_executable("aria2c")

    return None


def _install_aria2c_windows():
    bindir = os.path.join(os.path.dirname(cache.path()), "bin")
    exe = os.path.join(bindir, "aria2c.exe")
    os.makedirs(bindir, exist_ok=True)

    if _find_executable(exe):
        return exe

    try:
        release = json.loads(_download_bytes(ARIA2_RELEASE_API))
        asset = _find_aria2c_windows_asset(release.get("assets", ()))
        if not asset:
            return None

        data = _download_bytes(asset["browser_download_url"])
        with zipfile.ZipFile(io.BytesIO(data)) as zfile:
            member = next(
                (name for name in zfile.namelist()
                 if name.rsplit("/", 1)[-1].lower() == "aria2c.exe"),
                None,
            )
            if not member:
                return None

            with zfile.open(member) as src, open(exe, "wb") as dst:
                shutil.copyfileobj(src, dst)
    except Exception as exc:
        log.warning("Unable to download aria2c automatically (%s: %s)",
                    exc.__class__.__name__, exc)
        return None

    return exe


def _find_aria2c_windows_asset(assets):
    arch = "64bit" if sys.maxsize > 2**32 else "32bit"
    suffix = f"-win-{arch}-build1.zip"
    for asset in assets:
        if asset.get("name", "").endswith(suffix):
            return asset
    return None


def _download_bytes(url):
    request = Request(url, headers={"User-Agent": util.USERAGENT_GALLERYDL})
    with urlopen(request) as response:
        return response.read()


def _install_python_package(package_name):
    for use_user in (False, True):
        if use_user and (util.EXECUTABLE or sys.prefix != sys.base_prefix):
            continue

        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
        ]
        if use_user:
            cmd.append("--user")
        cmd.append(package_name)

        if _run_command(cmd):
            if use_user:
                site.addsitedir(site.getusersitepackages())
            return True

    return False


def _run_command(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except OSError as exc:
        log.debug("Failed to run %s (%s: %s)",
                  cmd[0], exc.__class__.__name__, exc)
        return False

    if proc.returncode == 0:
        return True

    stderr = proc.stderr.decode(errors="replace").strip()
    if stderr:
        log.debug("%s failed: %s", cmd[0], stderr[-200:])
    else:
        log.debug("%s failed with exit code %s", cmd[0], proc.returncode)
    return False
