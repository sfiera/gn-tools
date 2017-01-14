#!/usr/bin/env python
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import shlex
import subprocess
import sys

FLAGS = {
    "include_dirs":  "--cflags-only-I",
    "cflags":        "--cflags-only-other",
    "lib_dirs":      "--libs-only-L",
    "libs":          "--libs-only-l",
    "ldflags":       "--libs-only-other",
}

def main():
    progname, library = sys.argv

    for gn_name, flag in FLAGS.iteritems():
        values = subprocess.check_output(["pkg-config", flag, "--", library])
        values = shlex.split(values)
        print("%s = %s" % (gn_name, json.dumps(values)))

if __name__ == "__main__":
    main()
