#!/usr/bin/env python3
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import division, print_function, unicode_literals
import contextlib
import json
import os
import platform
import subprocess
import sys

BUILDLIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(BUILDLIB, "bin")
BIN_NINJA = os.path.join(BIN, "ninja")
BIN_GN = os.path.join(BIN, "gn")


def host_os():
    if sys.platform == "darwin":
        return "mac"
    for platform in ["linux", "win"]:
        if sys.platform.startswith(platform):
            return platform
    return "unknown"


def host_cpu():
    cpu = platform.uname()[4]
    if cpu == "x86_64":
        return "x64"
    return cpu


def tint(text, color):
    if not (color and os.isatty(1)):
        return text
    color = {
        "red": 1,
        "green": 2,
        "yellow": 3,
        "blue": 4,
    }[color]
    return "\033[1;38;5;%dm%s\033[0m" % (color, text)


@contextlib.contextmanager
def step(message):
    sys.stdout.write(message + "...")
    sys.stdout.flush()
    padding = ((27 - len(message)) * " ")

    def msg(failure, color=None):
        print(padding + tint(failure, color))
        msg.called = True

    msg.called = False
    yield msg
    if not msg.called:
        print(padding + tint("ok", "green"))


def check_bin(cmdline, what=None, input=None):
    if what is None:
        what = cmdline[0]
    with step("checking for %s" % what) as msg:
        stdin = None
        if input is not None:
            stdin = subprocess.PIPE
            if not isinstance(input, bytes):
                input = input.encode("utf-8")
        try:
            p = subprocess.Popen(cmdline,
                                 stdin=stdin,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            p.communicate(input)
            if p.returncode == 0:
                return True
        except OSError:
            pass
        msg("missing", color="red")
        return False


def check_pkg(lib):
    with step("checking for %s" % lib) as msg:
        try:
            p = subprocess.Popen(["pkg-config", lib])
            p.communicate()
            if p.returncode == 0:
                return True
        except OSError:
            pass
        msg("missing", color="red")
        return False


def check_gn():
    """Check that gn --version succeeds"""
    return check_bin([BIN_GN, "--version"], what="gn")


def check_ninja():
    """Check that ninja --version succeeds"""
    return check_bin([BIN_NINJA, "--version"], what="ninja")


def check_clang(executable=""):
    """Compile a basic C++11 binary."""
    executable = executable or "clang++"
    return check_bin(("%s -x c++ -std=c++11 - -o /dev/null" % executable).split(),
                     what="clang",
                     input="int main() { return 1; }")


def check_libcxx(executable=""):
    """Compile a basic C++11, libc++ binary."""
    executable = executable or "clang++"
    return check_bin(
        ("%s -x c++ -std=c++11 -stdlib=libc++ - -o /dev/null" % executable).split(),
        what="libc++",
        input="#include <chrono>\n\nint main() { return std::chrono::seconds(1).count(); }")


def check_libcxxabi(executable=""):
    """Compile a basic C++11, libc++ binary, including cxxabi.h.

    Pass -I/usr/include/libcxxabi explicitly to work around a broken
    environment on Ubuntu.
    """
    executable = executable or "clang++"
    return check_bin(
        ("%s -x c++ -std=c++11 -stdlib=libc++ -I/usr/include/libcxxabi - -o /dev/null" %
         executable).split(),
        what="libc++abi",
        input="#include <cxxabi.h>\n\nint main() { return 0; }")


def check_pkg_config():
    """Run pkg-config --version."""
    return check_bin("pkg-config --version".split())


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != 17:
            raise


def gn(**kwds):
    target_os = kwds["target_os"]
    mode = kwds["mode"]
    out = os.path.join("out", target_os, mode)

    gn_args = " ".join('%s = %s' % (k, json.dumps(v)) for k, v in kwds.items())
    cmd = ["gn", "gen", "--export-compile-commands", "-q", out, "--args=%s" % gn_args]
    with step("generating build.ninja") as msg:
        try:
            os.makedirs("out")
        except OSError as e:
            if e.errno != 17:
                raise

        try:
            os.unlink("out/cur")
        except OSError as e:
            pass
        os.symlink(os.path.join(target_os, mode), "out/cur")

        retcode = subprocess.call(cmd)
        if retcode != 0:
            msg("failed", color="red")
            sys.exit(retcode)
