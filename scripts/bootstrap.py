#!/usr/bin/env python3

import os
import pipes
import subprocess

BUILDLIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(BUILDLIB, "bin")
BIN_NINJA = os.path.join(BIN, "ninja")
BIN_GN = os.path.join(BIN, "gn")

ROOT = os.path.dirname(os.path.dirname(BUILDLIB))
EXT = os.path.join(ROOT, "ext")
EXT_NINJA = os.path.join(EXT, "ninja")
EXT_GN = os.path.join(EXT, "gn")


def main():
    if not os.path.exists(BIN_NINJA):
        build_ninja()
    if not os.path.exists(BIN_GN):
        build_gn()


def build_ninja():
    cd(EXT_NINJA)
    run("python3 ./configure.py --bootstrap".split())


def build_gn():
    cd(EXT_GN)
    run("python3 build/gen.py".split())
    run("../ninja/ninja -C out gn".split())


def cd(dir):
    print("CD %s" % pipes.quote(dir))
    os.chdir(dir)


def run(command):
    print("RUN %s" % " ".join(pipes.quote(arg) for arg in command))
    subprocess.check_call(command)


if __name__ == "__main__":
    main()
