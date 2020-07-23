#!/usr/bin/env python3
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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


_KNOWN_PROTOS = frozenset("debian fedora arch alpine suse gentoo slackware".split())


def dist_proto():
    """Returns a pair (pretty name, prototype) based on os-release.

    For example, if the distribution is “Debian-like” (such as Ubuntu or
    Raspbian), then the returned prototype would be “debian”.
    """
    values = {}
    try:
        with open("/etc/os-release") as f:
            return _load_dist_proto(f)
    except (OSError, IOError):
        return ("Unknown", "unknown")


def _load_dist_proto(lines):
    values = {}
    for line in lines:
        k, v = line.split("=", 1)
        v, = shlex.split(v)
        values[k] = v
    pretty = values.get("PRETTY_NAME", "Unknown")
    ids = set([values["ID"]]).union(values.get("ID_LIKE", "").split())
    matches = ids & _KNOWN_PROTOS
    if matches:
        return pretty, matches.pop()
    return pretty, "unknown"


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


def check_brew():
    """Check that brew --version succeeds"""
    return check_bin("brew --version".split(), what="brew")


def check_gn():
    """Check that gn --version succeeds"""
    return check_bin("gn --version".split(), what="gn")


def check_ninja():
    """Check that ninja --version succeeds"""
    return check_bin("ninja --version".split(), what="ninja")


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
    """Compile a basic C++11, libc++ binary, including cxxabi.h."""
    executable = executable or "clang++"
    return check_bin(("%s -x c++ -std=c++11 -stdlib=libc++ - -o /dev/null" % executable).split(),
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
