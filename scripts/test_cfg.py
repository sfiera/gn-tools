#!/usr/bin/env python3
#
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import cfg

RASPBIAN = """
PRETTY_NAME="Raspbian GNU/Linux 10 (buster)"
NAME="Raspbian GNU/Linux"
VERSION_ID="10"
VERSION="10 (buster)"
VERSION_CODENAME=buster
ID=raspbian
ID_LIKE=debian
HOME_URL="http://www.raspbian.org/"
SUPPORT_URL="http://www.raspbian.org/RaspbianForums"
BUG_REPORT_URL="http://www.raspbian.org/RaspbianBugs"
""".strip().split(
    "\n"
)

XENIAL = """
NAME="Ubuntu"
VERSION="16.04.6 LTS (Xenial Xerus)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 16.04.6 LTS"
VERSION_ID="16.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
VERSION_CODENAME=xenial
UBUNTU_CODENAME=xenial
""".strip().split(
    "\n"
)

SID = """
PRETTY_NAME="Debian GNU/Linux bullseye/sid"
NAME="Debian GNU/Linux"
ID=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
""".strip().split(
    "\n"
)

CENTOS = """
NAME="CentOS Linux"
VERSION="8 (Core)"
ID="centos"
ID_LIKE="rhel fedora"
VERSION_ID="8"
PLATFORM_ID="platform:el8"
PRETTY_NAME="CentOS Linux 8 (Core)"
ANSI_COLOR="0;31"
CPE_NAME="cpe:/o:centos:centos:8"
HOME_URL="https://www.centos.org/"
BUG_REPORT_URL="https://bugs.centos.org/"

CENTOS_MANTISBT_PROJECT="CentOS-8"
CENTOS_MANTISBT_PROJECT_VERSION="8"
REDHAT_SUPPORT_PRODUCT="centos"
REDHAT_SUPPORT_PRODUCT_VERSION="8"
""".strip().split(
    "\n"
)

ARCHLINUX = """
NAME="Arch Linux"
PRETTY_NAME="Arch Linux"
ID=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;23;147;209"
HOME_URL="https://www.archlinux.org/"
DOCUMENTATION_URL="https://wiki.archlinux.org/"
SUPPORT_URL="https://bbs.archlinux.org/"
BUG_REPORT_URL="https://bugs.archlinux.org/"
LOGO=archlinux
""".strip().split(
    "\n"
)

ALPINE = """
NAME="Alpine Linux"
ID=alpine
VERSION_ID=3.12.0
PRETTY_NAME="Alpine Linux v3.12"
HOME_URL="https://alpinelinux.org/"
BUG_REPORT_URL="https://bugs.alpinelinux.org/"
""".strip().split(
    "\n"
)

UNKNOWN = """
PRETTY_NAME="Crazy Other Linux"
ID=crazy
""".strip().split(
    "\n"
)


def test_rasbpian_proto():
    detect = cfg._detect_dist_proto

    assert detect(RASPBIAN) == cfg.proto(
        "Raspbian GNU/Linux 10 (buster)", "debian", "buster"
    )
    assert detect(XENIAL) == cfg.proto("Ubuntu 16.04.6 LTS", "debian", "xenial")
    assert detect(SID) == cfg.proto(
        "Debian GNU/Linux bullseye/sid", "debian", "unknown"
    )
    assert detect(CENTOS) == cfg.proto("CentOS Linux 8 (Core)", "fedora", "unknown")
    assert detect(ARCHLINUX) == cfg.proto("Arch Linux", "arch", "unknown")
    assert detect(ALPINE) == cfg.proto("Alpine Linux v3.12", "alpine", "unknown")
    assert detect(UNKNOWN) == cfg.proto("Crazy Other Linux", "unknown", "unknown")

    assert detect([]) == cfg.proto("Unknown", "unknown", "unknown")
