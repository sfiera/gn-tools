#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
#
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import, division, print_function, unicode_literals
import io
import os
import sys
import requests
import zipfile

PACKAGE = os.path.dirname(os.path.dirname(__file__))
BINDIR = os.path.join(PACKAGE, "bin")
PLATFORMS = {
    "mac": ("mac", "amd64", ""),
    "linux": ("linux", "amd64", ""),
    "win": ("windows", "amd64", ".exe"),
}


def main():
    assert not sys.argv[1:]  # Script takes no arguments
    try:
        download_gn()
        download_ninja()
    except Exception as e:
        print(e)
        sys.exit(1)


def download_gn():
    for platform, (sys, arch, ext) in PLATFORMS.items():
        path = os.path.join(BINDIR, platform, arch, "gn" + ext)
        print("updating %s…" % path)
        repo = "https://chrome-infra-packages.appspot.com/dl/gn/gn"
        resp = requests.get("%s/%s-%s/+/latest" % (repo, sys, arch))
        resp.raise_for_status()

        data = io.BytesIO(resp.content)
        z = zipfile.ZipFile(data)
        with open(path, "wb") as f:
            f.write(z.open("gn" + ext).read())
        os.chmod(path, 0o755)


def download_ninja():
    latest = requests.get("https://api.github.com/repos/ninja-build/ninja/releases/latest")
    latest.raise_for_status()

    for asset in latest.json()["assets"]:
        name = asset["name"]
        if not (name.startswith("ninja-") and name.endswith(".zip")):
            continue
        platform = name[6:-4]
        if platform not in PLATFORMS:
            continue
        _, arch, ext = PLATFORMS[platform]

        path = os.path.join(BINDIR, platform, arch, "ninja" + ext)
        print("updating %s…" % path)
        resp = requests.get(asset["browser_download_url"])
        resp.raise_for_status()

        data = io.BytesIO(resp.content)
        z = zipfile.ZipFile(data)
        with open(path, "wb") as f:
            f.write(z.open("ninja" + ext).read())
        os.chmod(path, 0o755)


if __name__ == "__main__":
    main()
