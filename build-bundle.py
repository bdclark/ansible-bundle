#!/usr/bin/env python
"""Script to create self contained install.

The goal of this script is simple:

  * Create a self contained install of Ansible that
    requires no external resources during installation.

It does this by using all the normal python tooling
(virtualenv, pip) but provides a simple, easy to use
interface for those not familiar with the python
ecosystem.
"""

from __future__ import print_function

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
from contextlib import contextmanager

PACKAGE_DEPS = [
    ("appdirs", "1.4.4", False),
    ("cffi", "1.14.0", True),
    ("cryptography", "2.9.2", True),
    ("distlib", "0.3.1", False),
    ("filelock", "3.0.12", False),
    ("Jinja2", "2.11.2", False),
    ("MarkupSafe", "1.1.1", False),
    ("pycparser", "2.20", False),
    ("PyYAML", "5.3.1", False),
    ("six", "1.15.0", False),
    ("virtualenv", "16.7.10", False),
    ("enum34", "1.1.10", False),
    ("ipaddress", "1.0.23", False),
    ("wheel", "0.34.2", False),
]
PLATFORMS = {
    "linux_x86_64": ["manylinux1_x86_64", "manylinux2010_x86_64"],
    "macosx_x86_64": ["macosx_10_10_x86_64"],
}
PYTHON_VERSIONS = ["2.7", "3.5", "3.6", "3.7", "3.8"]

BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
ZIP_FILENAME = "ansible-bundle.zip"
ZIP_DIRNAME = "ansible-bundle"


def fail(msg, exit_code=1):
    """Exit script with error and message."""
    sys.stderr.write("{}\n".format(msg))
    sys.exit(exit_code)


@contextmanager
def cd(dirname):
    """Change into dirname directory."""
    original = os.getcwd()
    os.chdir(dirname)
    try:
        yield
    finally:
        os.chdir(original)


def run(cmd):
    """Execute a sub-process."""
    print("Running cmd: %s" % cmd)
    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = p.communicate()
    rc = p.wait()
    if p.returncode != 0:
        fail("Non-zero exit code (%s) for cmd '%s': %s" % (rc, cmd, stderr + stdout))
    return stderr + stdout


def create_scratch_dir():
    """Create the dir where all bundling occurs."""
    dirname = os.path.join(BUILD_DIR, "scratch")
    if os.path.isdir(dirname):
        shutil.rmtree(dirname)
    package_dir = os.path.join(dirname, "packages")
    os.makedirs(package_dir)
    return dirname, package_dir


def download_packages(dirname, ansible_version, other_packages, platform):
    """Download packages from PyPi."""
    with cd(dirname):
        _download_package_tarball(dirname, "ansible", ansible_version)
        for package, version, binary in other_packages:
            if binary:
                _download_binary_package(dirname, package, version, platform)
            else:
                _download_package_tarball(dirname, package, version)


def _download_package_tarball(dirname, package, version):
    run(
        "%s -m pip download %s==%s --no-binary :all: --no-deps"
        % (sys.executable, package, version)
    )


def _download_binary_package(dirname, package, version, platform):
    for platform_ver in PLATFORMS[platform]:
        for python_ver in PYTHON_VERSIONS:
            cmd = (
                "%s -m pip download %s==%s --only-binary :all: "
                "--platform %s --python-version %s --no-deps"
            ) % (sys.executable, package, version, platform_ver, python_ver)
            if python_ver == "2.7" and platform == "linux_x86_64":
                for abi in ["cp27m", "cp27mu"]:
                    run("%s --abi %s" % (cmd, abi))
            else:
                run(cmd)


def _remove_cli_zip(scratch_dir):
    clidir = [f for f in os.listdir(scratch_dir) if f.startswith("awscli")]
    assert len(clidir) == 1
    os.remove(os.path.join(scratch_dir, clidir[0]))


def create_bootstrap_script(scratch_dir):
    """Copy install script to scratch_dir."""
    install_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install")
    shutil.copy(install_script, os.path.join(scratch_dir, "install"))


def create_tarball(scratch_dir, tarball_filename, cleanup=True):
    """Create gzipped tarball from scratch_dir contents."""
    dirname, tmpdir = os.path.split(scratch_dir)
    with cd(dirname):
        with tarfile.open(tarball_filename, "w:gz") as tar:
            tar.add(scratch_dir, arcname=ZIP_DIRNAME)
    if cleanup:
        shutil.rmtree(scratch_dir)
    return os.path.join(dirname, tarball_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ansible_version")
    parser.add_argument(
        "--platform",
        choices=PLATFORMS.keys(),
        default="linux_x86_64",
        help="Platform for binary packages (default: linux_x86_64",
    )
    args = parser.parse_args()

    scratch_dir, package_dir = create_scratch_dir()
    print("Bundle dir at: {}".format(scratch_dir))
    download_packages(
        dirname=package_dir,
        ansible_version=args.ansible_version,
        other_packages=PACKAGE_DEPS,
        platform=args.platform,
    )
    create_bootstrap_script(scratch_dir)
    tarball = "ansible-bundle-{}-{}.tgz".format(args.ansible_version, args.platform)
    tarball = create_tarball(scratch_dir, tarball)
    print("Bundled Ansible installer is at: {}".format(tarball))
