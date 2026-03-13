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
SYSTEM_PACKAGE_MANAGERS = (
    ("apt-get", True, ("install", "-y")),
    ("dnf"    , True, ("install", "-y")),
    ("yum"    , True, ("install", "-y")),
    ("pacman" , True, ("-S", "--noconfirm")),
    ("zypper" , True, ("--non-interactive", "install")),
    ("apk"    , True, ("add",)),
    ("brew"   , False, ("install",)),
)
SYSTEM_PACKAGES = {
    "aria2c"  : {
        "apt-get": "aria2",
        "dnf"    : "aria2",
        "yum"    : "aria2",
        "pacman" : "aria2",
        "zypper" : "aria2",
        "apk"    : "aria2",
        "brew"   : "aria2",
    },
    "ffmpeg"  : {
        "apt-get": "ffmpeg",
        "dnf"    : "ffmpeg",
        "yum"    : "ffmpeg",
        "pacman" : "ffmpeg",
        "zypper" : "ffmpeg",
        "apk"    : "ffmpeg",
        "brew"   : "ffmpeg",
    },
    "mkvmerge": {
        "apt-get": "mkvtoolnix",
        "dnf"    : "mkvtoolnix",
        "yum"    : "mkvtoolnix",
        "pacman" : "mkvtoolnix-cli",
        "zypper" : "mkvtoolnix",
        "apk"    : "mkvtoolnix",
        "brew"   : "mkvtoolnix",
    },
}
WINDOWS_PACKAGE_MANAGERS = (
    ("winget", False, (
        "install",
        "--silent",
        "--disable-interactivity",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--id",
    )),
    ("choco" , False, ("install", "-y")),
)
WINDOWS_PACKAGES = {
    "aria2c"  : {
        "winget": "aria2.aria2",
        "choco" : "aria2",
    },
    "ffmpeg"  : {
        "winget": "Gyan.FFmpeg",
        "choco" : "ffmpeg",
    },
    "mkvmerge": {
        "winget": "MoritzBunkus.MKVToolNix",
        "choco" : "mkvtoolnix",
    },
}
OPTIONAL_PYTHON_PACKAGES = (
    {
        "label"  : "yt-dlp or youtube-dl",
        "modules": ("yt_dlp", "youtube_dl"),
        "package": "yt-dlp[default]",
    },
    {
        "label"  : "PySocks",
        "modules": ("socks",),
        "package": "requests[socks]",
    },
    {
        "label"  : "brotli or brotlicffi",
        "modules": ("brotli", "brotlicffi"),
        "package": "brotli",
    },
    {
        "label"  : "zstandard",
        "modules": ("zstandard",),
        "package": "zstandard",
    },
    {
        "label"  : "PyYAML",
        "modules": ("yaml",),
        "package": "pyyaml",
    },
    {
        "label"  : "toml",
        "modules": ("tomllib", "toml"),
        "package": "toml",
        "skip"   : lambda: (
            "provided by the standard library on Python 3.11+"
            if sys.version_info >= (3, 11) else None
        ),
    },
    {
        "label"  : "SecretStorage",
        "modules": ("secretstorage",),
        "package": "secretstorage",
        "skip"   : lambda: (
            None if sys.platform.startswith("linux")
            else "not supported on this platform"
        ),
    },
    {
        "label"  : "Psycopg",
        "modules": ("psycopg",),
        "package": "psycopg[binary]",
    },
    {
        "label"  : "truststore",
        "modules": ("truststore",),
        "package": "truststore",
        "skip"   : lambda: (
            None if sys.version_info >= (3, 10)
            else "requires Python 3.10+"
        ),
    },
    {
        "label"  : "Jinja",
        "modules": ("jinja2",),
        "package": "jinja2",
    },
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


def install_optional_dependencies():
    """Install optional README dependencies in a non-interactive manner."""
    success = True

    _announce("Installing optional dependencies listed in the README")

    for executable in ("aria2c", "ffmpeg", "mkvmerge"):
        success = _install_optional_executable(executable) and success

    for dep in OPTIONAL_PYTHON_PACKAGES:
        success = _install_optional_python_package(dep) and success

    if success:
        _announce("Optional dependency installation finished")
    else:
        _announce("Optional dependency installation finished with failures")
    return success


def _find_executable(command):
    return shutil.which(command)


def _install_aria2c_package():
    if _install_system_package("aria2c"):
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


def _announce(message):
    log.info(message)
    sys.stderr.write(message + "\n")


def _install_optional_executable(command):
    if _find_executable(command):
        _announce(f"{command}: already installed")
        return True

    _announce(f"{command}: installing")

    if command == "aria2c":
        result = ensure_aria2c(command)
        success = _is_aria2c_installed(result, command)
    else:
        success = _install_system_package(command)

    if success:
        _announce(f"{command}: installed")
    else:
        _announce(f"{command}: unable to install automatically")
    return success


def _install_optional_python_package(dep):
    skip_reason = dep.get("skip", lambda: None)()
    if skip_reason:
        _announce(f"{dep['label']}: skipped ({skip_reason})")
        return True

    if any(_find_python_module(name) for name in dep["modules"]):
        _announce(f"{dep['label']}: already installed")
        return True

    _announce(f"{dep['label']}: installing")
    if _install_python_package(dep["package"]):
        _announce(f"{dep['label']}: installed")
        return True

    _announce(f"{dep['label']}: unable to install automatically")
    return False


def _install_system_package(name):
    if util.WINDOWS:
        managers = WINDOWS_PACKAGE_MANAGERS
        packages = WINDOWS_PACKAGES[name]
        sudo = None
        needs_root = False
    else:
        managers = SYSTEM_PACKAGE_MANAGERS
        packages = SYSTEM_PACKAGES[name]
        sudo = shutil.which("sudo")
        needs_root = hasattr(os, "geteuid") and os.geteuid() != 0

    for manager, require_root, args in managers:
        package = packages.get(manager)
        if not package or not shutil.which(manager):
            continue

        cmd = [manager, *args, package]
        if require_root and needs_root:
            if not sudo:
                continue
            cmd = [sudo, "-n", *cmd]

        if _run_command(cmd):
            return True

    return False


def _is_aria2c_installed(result, executable_name):
    return bool(result and result != executable_name)


def _install_python_package(package_name):
    if not _find_python_module("pip"):
        if not _install_pip():
            return False

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


def _find_python_module(name):
    try:
        return importlib.util.find_spec(name)
    except (AttributeError, ImportError, ValueError):
        return None


def _install_pip():
    if not _find_python_module("ensurepip"):
        return False

    log.info("Attempting to install missing pip")
    return _run_command([
        sys.executable,
        "-m",
        "ensurepip",
        "--default-pip",
    ])


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
