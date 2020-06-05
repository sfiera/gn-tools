#!/usr/bin/env python3
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys


def main():
    progname, origin, header, source, symbol = sys.argv
    symbol = symbol.split("::")

    with open(origin) as f:
        data = f.readlines()

    with open(header, "w") as f:
        f.write("// THIS FILE WAS AUTOMATICALLY GENERATED; DO NOT EDIT\n")
        f.write("\n")
        for namespace in symbol[:-1]:
            f.write("namespace %s {\n" % namespace)
        f.write("\n")
        f.write("extern const char %s[];\n" % symbol[-1])
        f.write("\n")
        for namespace in symbol[-2::-1]:
            f.write("}  // namespace %s\n" % namespace)

    with open(source, "w") as f:
        f.write("// THIS FILE WAS AUTOMATICALLY GENERATED; DO NOT EDIT\n")
        f.write("\n")
        for namespace in symbol[:-1]:
            f.write("namespace %s {\n" % namespace)
        f.write("\n")
        f.write("extern const char %s[] =\n" % symbol[-1])
        for line in data:
            f.write("    \"%s\"\n" % escape(line))
        f.write(";\n")
        f.write("\n")
        for namespace in symbol[-2::-1]:
            f.write("}  // namespace %s\n" % namespace)


def escape(s):
    if len(s) != 1:
        return "".join(escape(ch) for ch in s)

    if s in "\t\n\r":
        return {"\t": r"\t", "\n": r"\n", "\r": r"\r"}[s]
    elif " " <= s <= "~":
        return s
    return r"\%03o" % ord(s)


if __name__ == "__main__":
    main()
