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
import textwrap


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
            p = subprocess.Popen(shlex.split(executable) + args,
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


PKG_CONFIG_FLAGS = {
    "include_dirs": ("--cflags-only-I", "-I"),
    "cflags": ("--cflags-only-other", ""),
    "lib_dirs": ("--libs-only-L", "-L"),
    "libs": ("--libs-only-l", "-l"),
    "ldflags": ("--libs-only-other", ""),
}


def check_pkg(executable, lib):
    flags = {}
    with step("checking for %s" % lib) as msg:
        try:
            for gn_name, (flag, prefix) in PKG_CONFIG_FLAGS.items():
                values = subprocess.check_output(shlex.split(executable) + [flag, "--", lib],
                                                 stderr=subprocess.DEVNULL)
                values = values.decode("utf-8")
                values = [_strip_prefix(prefix, x) for x in shlex.split(values)]
                flags[gn_name] = values
        except (OSError, subprocess.CalledProcessError):
            msg("missing", color="red")
            return None
    return flags


def _strip_prefix(prefix, s):
    if s.startswith(prefix):
        return s[len(prefix):]
    return s


def check_brew(default="brew"):
    """Check that brew --version succeeds"""
    executable = os.getenv("BREW", default)
    return check_bin(executable, ["--version"], what="brew")


def check_gn(default="gn"):
    """Check that gn --version succeeds"""
    executable = os.getenv("GN", default)
    return check_bin(executable, ["--version"], what="gn")


def check_ninja(default="ninja"):
    """Check that ninja --version succeeds"""
    executable = os.getenv("NINJA", default)
    return check_bin(executable, ["--version"], what="ninja")


def check_clang(default="clang"):
    """Compile a basic C99 binary."""
    executable = os.getenv("CC", default)
    return check_bin(executable,
                     "-x c -std=c99 - -o /dev/null".split(),
                     what="clang",
                     input="int main() { return 1; }")


def check_clangxx(default="clang++"):
    """Compile a basic C++11 binary."""
    executable = os.getenv("CXX", default)
    return check_bin(executable,
                     "-x c++ -std=c++11 - -o /dev/null".split(),
                     what="clang++",
                     input="int main() { return 1; }")


def check_libcxx(default="clang++"):
    """Compile a basic C++11, libc++ binary."""
    executable = os.getenv("CXX", default)
    return check_bin(
        executable,
        "-x c++ -std=c++11 -stdlib=libc++ - -o /dev/null".split(),
        what="libc++",
        input="#include <chrono>\n\nint main() { return std::chrono::seconds(1).count(); }")


def check_libcxxabi(default="clang++"):
    """Compile a basic C++11, libc++ binary, including cxxabi.h."""
    executable = os.getenv("CXX", default)
    return check_bin(executable,
                     "-x c++ -std=c++11 -stdlib=libc++ - -o /dev/null".split(),
                     what="libc++abi",
                     input="#include <cxxabi.h>\n\nint main() { return 0; }")


def check_pkg_config(default="pkg-config"):
    """Run pkg-config --version."""
    executable = os.getenv("PKG_CONFIG", default)
    return check_bin(executable, ["--version"], what="pkg-config")


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != 17:
            raise


def gn(*, gn, ninja, **kwds):
    target_os = kwds["target_os"]
    mode = kwds["mode"]
    out = os.path.join("out", target_os, mode)

    gn_args = _gn_dumps(kwds)
    cmd = shlex.split(gn) + ["gen", "--export-compile-commands", "-q", out, "--args=%s" % gn_args]
    with step("generating build.ninja") as msg:
        try:
            os.makedirs("out")
        except OSError as e:
            if e.errno != 17:
                raise

        cur_path = os.path.join(target_os, mode)

        if host_os() == "win":
            try:
                os.mkdir(cur_path)
            except OSError:
                pass
        else:
            try:
                os.unlink("out/cur")
            except OSError as e:
                pass
            os.symlink(cur_path, "out/cur")

        retcode = subprocess.call(cmd)
        if retcode != 0:
            msg("failed", color="red")
            sys.exit(retcode)

        if host_os() != "win":
            with open("out/cur/ninja", "w") as f:
                f.write(
                    textwrap.dedent("""
                        #!/bin/sh
                        exec %s "$@"
                    """).lstrip() % ninja)
            os.chmod("out/cur/ninja", 0o755)


def _gn_dumps(obj):
    if isinstance(obj, (str, int, float)):
        return json.dumps(obj)
    elif isinstance(obj, (tuple, list)):
        return "[%s]" % ", ".join(_gn_dumps(x) for x in obj)
    elif isinstance(obj, dict):
        return "\n".join("%s = %s" % (k.replace("+", "x"), v) for k, v in _gn_obj_values(obj))
    raise TypeError(type(obj).__name__)


def _gn_obj_values(obj):
    for k, v in obj.items():
        if isinstance(v, (str, int, float, tuple, list)):
            yield k, _gn_dumps(v)
        elif isinstance(v, dict):
            for k2, v2 in _gn_obj_values(v):
                yield "%s_%s" % (k, k2), v2
        else:
            raise TypeError(type(obj).__name__)


Distro = collections.namedtuple("Distro", "name packages sources install update add_key".split())


def install_or_check(distros):
    import argparse

    if platform.system() == "Darwin":
        distro, codename = "mac", None
    elif platform.system() == "Linux":
        _, distro, codename = dist_proto()
    elif platform.system() == "Windows":
        distro, codename = "win", None
    else:
        sys.stderr.write("This script is Mac-, Linux-, and Windows-only, sorry.\n")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Install build deps for Antares")
    parser.add_argument("action", choices="check install".split())
    parser.add_argument("--distro", choices=sorted(distros.keys()), default=distro)
    parser.add_argument("--codename", type=str, default=codename)
    parser.add_argument("--dry-run", action="store_const", const=True, default=False)
    args, flags = parser.parse_known_args()

    distro = distros[args.distro]
    if args.action == "check":
        if not check_all(distro=distro, codename=args.codename):
            sys.exit(1)
    elif args.action == "install":
        install_all(distro=distro, codename=args.codename, dry_run=args.dry_run, flags=flags)


def check_all(*, distro, codename, prefix=""):
    checkers = {
        "clang": check_clang,
        "clang++": check_clangxx,
        "gn": check_gn,
        "ninja": check_ninja,
        "pkg-config": check_pkg_config,
    }

    pkg_config = None
    missing_pkgs = []
    config = {}
    for name in distro.packages:
        if name in checkers:
            dep = checkers[name]()
            if dep is None:
                missing_pkgs.append(name)
            else:
                config[name] = dep
            continue

        pkg_config = config.pop("pkg-config", pkg_config)
        if pkg_config is None:
            continue
        if not check_pkg(pkg_config, name):
            missing_pkgs.append(name)

    if not missing_pkgs:
        return config
    commands = []

    for name, url, component, key in distro.sources:
        path = "/etc/apt/sources.list.d/%s.list" % name
        if os.path.exists(path):
            continue
        commands.extend([
            _command(prefix, distro.add_key + [key]),
            "%s | %s" % (
                _command("", ["echo", "deb", url, codename, component]),
                _command(prefix, ["tee", path]),
            ),
        ])

    if distro.update:
        commands.append(_command(prefix, distro.update))
    missing_pkgs = sorted(set(distro.packages[pkg] for pkg in missing_pkgs))
    commands.append(_command(prefix, distro.install + missing_pkgs))

    print()
    print("missing dependencies: %s" % " ".join(missing_pkgs))
    if len(missing_pkgs) == 1:
        print("On %s, you can install it with:" % codename)
    else:
        print("On %s, you can install them with:" % codename)
    print()
    for command in commands:
        print("    $ %s" % command)
    print()
    print("Then, try ./configure again")
    return None


def install_all(*, distro, codename, dry_run=False, flags=[]):
    update = False
    for name, url, component, key in distro.sources:
        path = "/etc/apt/sources.list.d/%s.list" % name
        if os.path.exists(path):
            continue
        _run(dry_run, distro.add_key + [key])
        line = "deb %s %s %s" % (url, codename, component)
        _write(dry_run, line, path)
        update = True

    if update:
        _run(dry_run, distro.update)
    _run(dry_run, distro.install + list(distro.packages.values()) + flags)


def _command(prefix, args):
    return " ".join(shlex.quote(x) for x in shlex.split(prefix) + args)


def _run(dry_run, command):
    print(" ".join(shlex.quote(arg) for arg in command))
    if not dry_run:
        subprocess.check_call(command)


def _write(dry_run, content, path):
    print("+ tee %s" % shlex.quote(path))
    print(content)
    if not dry_run:
        with open(path, "w") as f:
            f.write(content)


def configure(project, distros, config):
    for k, v in check_deps(project, distros, config).items():
        if k not in config:
            config[k] = v

    script_executable = "python3"
    if host_os() == "win":
        script_executable = "python"

    with open('.gn', 'w') as gnf:
        gnf.write('buildconfig = "//build/BUILDCONFIG.gn"\n')
        gnf.write('script_executable = "' + script_executable + '"\n')

    with step("configure mode") as msg:
        msg(config["mode"], color="green")
    gn(**config)

    print("make(1) it so!")


def check_deps(project, distros, config):
    with step("checking host os") as msg:
        if host_os() in ["mac", "linux", "win"]:
            msg(host_os(), color="green")
        else:
            msg(host_os(), color="red")
            print("\nSorry! %s requires Mac OS X, Linux, or Windows" % project)
            sys.exit(1)

    with step("checking target os") as msg:
        if config["target_os"] is None:
            config["target_os"] = host_os()
        checker = {
            ("mac", "mac"): check_mac,
            ("linux", "linux"): check_linux_native,
            ("linux", "win"): check_win_on_linux,
            ("win", "win"): check_win_native,
        }.get((host_os(), config["target_os"]))
        if checker is None:
            msg(config["target_os"], color="red")
            sys.exit(1)
        msg(config["target_os"], color="green")

    return checker(project, distros)


def check_mac(project, distros):
    with step("checking Mac OS X version") as msg:
        ver = platform.mac_ver()[0]
        ver = tuple(int(x) for x in ver.split(".")[:2])
        if ver < (10, 9):
            msg("%d.%d" % ver, color="red")
            print("\nSorry! %s requires Mac OS X 10.9+" % project)
            sys.exit(1)
        msg("%d.%d" % ver, color="green")

    missing = collections.OrderedDict()
    if not (check_clang() and check_libcxx()):
        missing["xcode"] = ("* To install Xcode, open the App Store:\n"
                            "    https://itunes.apple.com/en/app/xcode/id497799835\n"
                            "  After installing, open it and accept the license agreement\n")
    if not check_brew():
        missing["brew"] = (
            "* To install Homebrew, run:\n"
            '    $ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"\n'
        )

    if missing:
        print("\nmissing dependencies: %s\n" % " ".join(missing.keys()))
        for dep in missing.values():
            sys.stdout.write(dep)
        print("")
        print("Then, try ./configure again")
        sys.exit(1)

    config = check_all(distro=distros["mac"], codename="mac")
    if config is None:
        sys.exit(1)
    return config


def check_linux_native(project, distros):
    with step("checking Linux distro") as msg:
        pretty, distro, codename = dist_proto()
        if distro in distros:
            msg(pretty, color="green")
        else:
            msg(pretty + " (untested)", color="yellow")
            distro = "debian"
    config = check_all(distro=distros[distro], codename=codename, prefix="sudo")
    if config is None:
        sys.exit(1)
    return config


def check_win_native(project, distros):
    config = check_all(distro=distros["win"], codename="win")
    if config is None:
        sys.exit(1)
    return config


def check_win_on_linux(project):
    with step("checking Linux distro") as msg:
        pretty, distro, codename = dist_proto()
        if (distro, codename) == ("debian", "focal"):
            msg(pretty, color="green")
        else:
            msg(pretty, color="red")
            print("\nSorry! Cross-compilation currently requires Ubuntu 20.04 focal")
            sys.exit(1)

    missing = collections.OrderedDict()
    if not check_clang("clang++"):
        missing["clang"] = "clang"

    with step("checking for mingw") as msg:
        if os.path.exists("/usr/x86_64-w64-mingw32/include/windows.h"):
            msg("ok", color="green")
        else:
            msg("missing", color="red")
            missing["mingw"] = "mingw-w64"

    if missing:
        print("\nmissing dependencies: %s" % " ".join(missing.keys()))
        if len(missing) == 1:
            print("\nYou can install it with:\n")
        else:
            print("\nYou can install them with:\n")
        print("    $ sudo apt-get install %s" % (" ".join(missing.values())))
        sys.exit(1)

    return {
        "ninja": "ninja",
        "gn": "gn",
    }
