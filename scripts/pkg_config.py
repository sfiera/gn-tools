#!/usr/bin/env python3
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import shlex
import subprocess
import sys

FLAGS = {
    "include_dirs": ("--cflags-only-I", "-I"),
    "cflags": ("--cflags-only-other", ""),
    "lib_dirs": ("--libs-only-L", "-L"),
    "libs": ("--libs-only-l", "-l"),
    "ldflags": ("--libs-only-other", ""),
}


def main():
    progname, library = sys.argv

    for gn_name, (flag, prefix) in FLAGS.items():
        values = subprocess.check_output(["pkg-config", flag, "--", library])
        values = values.decode("utf-8")
        values = [strip_prefix(prefix, x) for x in shlex.split(values)]
        print("%s = %s" % (gn_name, json.dumps(values)))


def strip_prefix(prefix, s):
    if s.startswith(prefix):
        return s[len(prefix) :]
    return s


if __name__ == "__main__":
    main()
