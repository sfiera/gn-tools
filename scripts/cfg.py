#!/usr/bin/env python3
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import json
import os
import platform
import shlex
import subprocess
import sys


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


proto = collections.namedtuple("proto", "pretty prototype codename".split())
_KNOWN_PROTOS = frozenset("debian fedora arch alpine suse gentoo slackware".split())


def dist_proto():
    """Returns a pair (pretty name, prototype, codename) based on os-release.

    For example, if the distribution is “Debian-like” (such as Ubuntu or
    Raspbian), then the returned prototype would be “debian”.
    """
    try:
        with open("/etc/os-release") as f:
            return _detect_dist_proto(f)
    except FileNotFoundError:
        return proto("Unknown", "unknown", "unknown")


def _detect_dist_proto(lines):
    values = {}
    for line in lines:
        line = line.strip()
        if line:
            k, v = line.split("=", 1)
            values[k], = shlex.split(v)

    pretty = values.get("PRETTY_NAME", "Unknown")
    codename = values.get("VERSION_CODENAME", "unknown")

    if values.get("ID") in _KNOWN_PROTOS:
        return proto(pretty, values["ID"], codename)

    like = set(values.get("ID_LIKE", "").split()) & _KNOWN_PROTOS
    if like:
        return proto(pretty, like.pop(), codename)

    return proto(pretty, "unknown", codename)


def check_bin(executable, args, *, what, input=None):
    with step("checking for %s" % what) as msg:
        stdin = None
        if input is not None:
            stdin = subprocess.PIPE
            if not isinstance(input, bytes):
                input = input.encode("utf-8")
        try:
            p = subprocess.Popen(executable + args,
                                 stdin=stdin,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            p.communicate(input)
            if p.returncode == 0:
                return executable
        except OSError:
            pass
        msg("missing", color="red")
        return None


def check_pkg(executable, lib):
    with step("checking for %s" % lib) as msg:
        try:
            p = subprocess.Popen(executable + [lib])
            p.communicate()
            if p.returncode == 0:
                return True
        except OSError:
            pass
        msg("missing", color="red")
        return False


def check_brew(default="brew"):
    """Check that brew --version succeeds"""
    executable = shlex.split(os.getenv("BREW", default))
    return check_bin(executable, ["--version"], what="brew")


def check_gn(default="gn"):
    """Check that gn --version succeeds"""
    executable = shlex.split(os.getenv("GN", default))
    return check_bin(executable, ["--version"], what="gn")


def check_ninja(default="ninja"):
    """Check that ninja --version succeeds"""
    executable = shlex.split(os.getenv("NINJA", default))
    return check_bin(executable, ["--version"], what="ninja")


def check_clang(default="clang++"):
    """Compile a basic C++11 binary."""
    executable = shlex.split(os.getenv("CXX", default))
    return check_bin(executable,
                     "-x c++ -std=c++11 - -o /dev/null".split(),
                     what="clang",
                     input="int main() { return 1; }")


def check_libcxx(default="clang++"):
    """Compile a basic C++11, libc++ binary."""
    executable = shlex.split(os.getenv("CXX", default))
    return check_bin(
        executable,
        "-x c++ -std=c++11 -stdlib=libc++ - -o /dev/null".split(),
        what="libc++",
        input="#include <chrono>\n\nint main() { return std::chrono::seconds(1).count(); }")


def check_libcxxabi(default="clang++"):
    """Compile a basic C++11, libc++ binary, including cxxabi.h."""
    executable = shlex.split(os.getenv("CXX", default))
    return check_bin(executable,
                     "-x c++ -std=c++11 -stdlib=libc++ - -o /dev/null".split(),
                     what="libc++abi",
                     input="#include <cxxabi.h>\n\nint main() { return 0; }")


def check_pkg_config(default="pkg-config"):
    """Run pkg-config --version."""
    executable = shlex.split(os.getenv("PKG_CONFIG", default))
    return check_bin(executable, ["--version"], what="pkg-config")


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
