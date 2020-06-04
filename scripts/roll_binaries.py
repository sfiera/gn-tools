#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import urllib2

PACKAGE = os.path.dirname(os.path.dirname(__file__))
BINDIR = os.path.join(PACKAGE, "bin")
EXTENSIONS = {
    "mac": "",
    "linux64": "",
    "win": ".exe",
}


def main():
    assert not sys.argv[1:]  # Script takes no arguments
    try:
        for host in ["mac", "linux64", "win"]:
            download_gn(host)
            download_ninja(host)
    except urllib2.HTTPError as e:
        print("%s: %s" % (e.geturl(), e))
        sys.exit(1)


def download_gn(host):
    path = os.path.join(BINDIR, host, "gn" + EXTENSIONS[host])
    print("updating %s…" % path)
    repo = "https://chromium.googlesource.com/chromium/buildtools/+/master"
    digest = get("%s/%s/gn%s.sha1?format=TEXT" % (repo, host, EXTENSIONS[host])).decode("base64")
    data = get("https://storage.googleapis.com/chromium-gn/%s" % digest)
    with open(path, "w") as f:
        f.write(data)
    os.chmod(path, 0o755)


def download_ninja(host):
    path = os.path.join(BINDIR, host, "ninja" + EXTENSIONS[host])
    print("updating %s…" % path)
    repo = "https://chromium.googlesource.com/chromium/tools/depot_tools.git/+/master"
    if host == "win":
        data = get("%s/ninja.exe?format=TEXT" % (repo)).decode("base64")
    else:
        data = get("%s/ninja-%s?format=TEXT" % (repo, host)).decode("base64")
    directory = os.path.join(BINDIR, host)
    with open(path, "w") as f:
        f.write(data)
    os.chmod(path, 0o755)


def get(url):
    return urllib2.urlopen(url).read()


if __name__ == "__main__":
    main()
