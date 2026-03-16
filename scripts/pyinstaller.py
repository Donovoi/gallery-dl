#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Build a standalone executable using Nuitka"""

import argparse
import subprocess
import util
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--os")
    parser.add_argument("-a", "--arch")
    parser.add_argument("-l", "--label")
    parser.add_argument("-e", "--extension")
    parser.add_argument("-p", "--print", action="store_true")
    return parser.parse_args(argv)


def make_label(args):
    if args.label:
        return args.label

    label = ""
    if args.os:
        os = args.os.partition("-")[0].lower()
        if os == "ubuntu":
            os = "linux"
        label += os
    if args.arch == "x86":
        label += "_x86"
    return label


def make_name(args):
    name = "gallery-dl"
    label = make_label(args)
    if label:
        name = "{}_{}".format(name, label)
    if args.extension:
        name = "{}.{}".format(name, args.extension.lower())
    return name


def build_command(args):
    return [
        sys.executable,
        "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--assume-yes-for-downloads",
        "--output-dir", util.path("build"),
        "--output-filename", util.path("dist", make_name(args)),
        util.path("gallery_dl", "__main__.py"),
    ]


def main():
    args = parse_args()
    label = make_label(args)
    if args.print:
        return print(label)

    return subprocess.call(build_command(args))


if __name__ == "__main__":
    sys.exit(main())
