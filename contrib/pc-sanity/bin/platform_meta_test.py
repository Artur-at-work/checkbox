#!/usr/bin/env python3
"""
Platform metapackage test script.

Checks if the correct OEM platform meta packages are installed for Dell systems.

Package Structure History:
    For somerville xenial-osp1 and after, there are two meta packages that should be installed:
    1. Platform meta package: PLATFORM_NAME-meta, e.g. turis-vegas-mlk-glk-meta
    2. BIOS ID meta package: dell-BIOS_ID-RELEASE-meta or dell-BIOS_ID-meta
       e.g. dell-086b-bionic-meta

    From somerville bionic-osp1 and after, the BIOS ID package is deprecated and replaced
    by modaliases in platform meta package:
    1. Platform meta package: oem-PLATFORM_NAME-meta, e.g. oem-beaver-osp1-worm-meta
    2. BIOS ID modaliases in platform meta package:
       e.g. Modaliases: hwe(pci:*sv00001028sd0000096E*, pci:*sv00001028sd0000096F*)

    For Sutton project (simon/newell/bachman), it must include 4-5 meta packages:
    - oem-ouagadougou-meta (group meta)
    - oem-sutton.bachman-factory-meta
    - oem-sutton.bachman-meta
    - oem-sutton.bachman-baara-meta (platform meta)
    - oem-sutton.bachman-factory-baara-meta
    Reference: https://trello.com/c/1E9nefUN/958-test-case-fix-the-meta-checking-for-sutton-pc-sanity

Usage:
    # Check Somerville platform
    python3 platform_meta_test.py --oem-codename somerville

    # Check Somerville with specific platform
    python3 platform_meta_test.py --oem-codename somerville --platform-codename turis-vegas-mlk-glk

    # Check Sutton platform (current name)
    python3 platform_meta_test.py --oem-codename sutton

    # Check Sutton with dotted variant
    python3 platform_meta_test.py --oem-codename sutton.bachman
    python3 platform_meta_test.py --oem-codename sutton.newell
    python3 platform_meta_test.py --oem-codename sutton.simon

    # Check Stella (accepted but no validation performed)
    python3 platform_meta_test.py --oem-codename stella

    # Check Stella with dotted variant (accepted but no validation performed)
    python3 platform_meta_test.py --oem-codename stella.cmit

Supported OEM Codenames:
    Current names (without dots):
    - somerville: Dell Somerville project (Xenial, Bionic, Focal, Jammy, Noble)
    - stella: Dell Stella project (no validation, returns success)
    - sutton: Dell Sutton project

    Dotted variants also supported:
    - stella.cmit: Dell Stella CMIT project
    - sutton.bachman: Dell Sutton Bachman project
    - sutton.newell: Dell Sutton Newell project
    - sutton.simon: Dell Sutton Simon project

Note:
    Stella variants (stella, stella.cmit) are accepted but currently just return
    success without performing any validation checks.

Exit Codes:
    0 - Test passed (correct meta packages found and installed)
    1 - Test failed (missing packages, BIOS mismatch, or other errors)
"""

import argparse
import subprocess
import sys
from typing import List, Optional, Tuple


class PlatformMetaTest:
    """Platform meta package validation."""

    def __init__(self, oem_codename: str, platform_codename: Optional[str] = None):
        self.oem = oem_codename
        self.platform_tag = platform_codename
        self.script_name = sys.argv[0]

    def passed(self, message: str = "") -> None:
        """Print success message and exit 0."""
        if message:
            print(message)
        print(f"{self.script_name} passed!")
        raise SystemExit(0)

    def failed(self, message: str = "") -> None:
        """Print failure message and exit 1."""
        if message:
            print(message)
        raise SystemExit(f"{self.script_name} failed!")

    def run_command(self, cmd: List[str], check: bool = False) -> Tuple[str, int]:
        """
        Run a shell command and return stdout and return code.

        Args:
            cmd: Command and arguments as list
            check: Whether to raise on non-zero exit

        Returns:
            Tuple of (stdout, returncode)
        """
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.stdout, result.returncode
        except subprocess.CalledProcessError as e:
            return e.stdout, e.returncode

    def read_dmi_file(self, filename: str) -> str:
        """Read a DMI file and return its content stripped."""
        path = f"/sys/devices/virtual/dmi/id/{filename}"
        # Use cat command so it can be mocked in tests
        stdout, returncode = self.run_command(["cat", path])
        if returncode != 0:
            self.failed(f"Cannot read {path}")
            return ""  # Never reached but makes type checker happy
        return stdout.strip()

    def get_installed_packages(self, pattern: str) -> List[str]:
        """Get list of installed packages matching pattern."""
        stdout, returncode = self.run_command(
            ["dpkg-query", "-W", "-f=${Package}\n", pattern]
        )
        if returncode != 0:
            return []
        return [pkg.strip() for pkg in stdout.split("\n") if pkg.strip()]

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        stdout, returncode = self.run_command(
            ["dpkg-query", "-W", "-f=${Status}\n", package]
        )
        return returncode == 0 and "install ok installed" in stdout

    def get_package_modaliases(self, package: str) -> Optional[str]:
        """Get Modaliases field from apt-cache show."""
        stdout, returncode = self.run_command(["apt-cache", "show", package])
        if returncode != 0:
            return None

        for line in stdout.split("\n"):
            if line.startswith("Modaliases:"):
                return line
        return None

    def has_modalias_match(self, package: str, pattern: str) -> bool:
        """Check if package modaliases contain pattern (case-insensitive)."""
        modaliases = self.get_package_modaliases(package)
        if not modaliases:
            return False
        return pattern.lower() in modaliases.lower()

    def prepare_somerville(self) -> Tuple[str, str]:
        """Prepare Somerville test - get BIOS ID and Ubuntu codename."""
        biosid = self.read_dmi_file("product_sku")
        stdout, _ = self.run_command(["lsb_release", "-cs"])
        ubuntu_codename = stdout.strip()
        return biosid, ubuntu_codename

    def prepare_sutton(self) -> str:
        """Prepare Sutton test - get BIOS ID from BIOS version (first 3 chars)."""
        bios = self.read_dmi_file("bios_version")
        return bios[:3]

    def check_stella_meta(self) -> None:
        """Accept Stella variants but perform no validation."""
        # Stella checking is not implemented yet - just return success
        print("not support stella.cmit yet.")
        raise SystemExit(0)

    def check_sutton_meta(self) -> None:
        """Check Sutton meta packages."""
        biosid = self.prepare_sutton()

        # Get meta packages matching pattern
        packages = self.get_installed_packages(f"oem-{self.oem}*-meta")
        meta_num = len(packages)

        # Must have exactly 4 packages
        if meta_num > 4:
            self.failed("Too many OEM meta packages!!!")
        elif meta_num == 0:
            self.failed("No OEM meta packages!!!")
        elif meta_num < 4:
            self.failed("Missing platform meta packages!!!")

        # Extract platform name from packages
        platform_tag = None
        for pkg in packages:
            parts = pkg.split("-")
            if len(parts) >= 3:
                platform_name = parts[2]

                # Skip factory and meta
                if platform_name == "factory":
                    continue
                if platform_name == "meta":
                    continue

                if platform_name:
                    platform_tag = platform_name
                    # Update oem in case there's no group name
                    self.oem = parts[1]
                    break

        if not platform_tag:
            self.failed("Missing platform meta packages!!!")

        # Check if meta package is installed and matches BIOS
        meta = f"oem-{self.oem}-{platform_tag}-meta"

        if not self.has_modalias_match(meta, f"bvr{biosid}"):
            self.failed(f"Meta package '{meta}' doesnt match BIOS ID '{biosid}'!!!")

        if not self.is_package_installed(meta):
            self.failed(f"Meta package '{meta}' is not installed!!!")

        # Check factory package
        factory = f"oem-{self.oem}-factory-{platform_tag}-meta"
        if not self.is_package_installed(factory):
            self.failed(f"Factory meta package '{factory}' is not installed!!!")

        self.passed(
            f"Found the platform meta package '{meta}' containing BIOS ID '{biosid}' "
            f"and the platform factory meta package '{factory}'"
        )

    def check_somerville_xenial(self, biosid: str) -> None:
        """Check Somerville meta packages for Xenial."""
        stdout, _ = self.run_command(["dpkg", "-l"])

        for line in stdout.split("\n"):
            parts = line.split()
            if len(parts) >= 2 and "-meta" in parts[1]:
                meta = parts[1]
                # Check pattern: dell-BIOSID-meta or dell-BIOSID-xenial-meta
                if meta in (f"dell-{biosid}-meta", f"dell-{biosid}-xenial-meta"):
                    # Get dependencies
                    dep_stdout, _ = self.run_command(["apt-cache", "depends", meta])
                    for dep_line in dep_stdout.split("\n"):
                        if "Depends:" in dep_line:
                            pmeta = dep_line.split()[1]
                            if "-meta" in pmeta:
                                self.passed(
                                    f"Found platform meta packages: {pmeta}, {meta}"
                                )

    def check_somerville_bionic(self, biosid: str) -> None:
        """Check Somerville meta packages for Bionic."""
        # Check old-style dell-BIOSID-bionic-meta
        stdout, _ = self.run_command(["dpkg", "-l"])

        for line in stdout.split("\n"):
            parts = line.split()
            if len(parts) >= 2 and "-meta" in parts[1]:
                meta = parts[1]
                # Check pattern: dell-BIOSID-meta or dell-BIOSID-bionic-meta
                if meta in (f"dell-{biosid}-meta", f"dell-{biosid}-bionic-meta"):
                    dep_stdout, _ = self.run_command(["apt-cache", "depends", meta])
                    for dep_line in dep_stdout.split("\n"):
                        if "Depends:" in dep_line:
                            pmeta = dep_line.split()[1]
                            if "-meta" in pmeta:
                                self.passed(
                                    f"Found platform meta packages: {pmeta}, {meta}"
                                )

        # Check platform-tag-meta
        if self.platform_tag:
            if self.is_package_installed(f"{self.platform_tag}-meta"):
                self.passed(f"Found platform meta package: {self.platform_tag}-meta")

            # Check oem-platform-tag-meta
            pmeta = f"oem-{self.platform_tag}-meta"
            if self.is_package_installed(pmeta):
                if self.has_modalias_match(pmeta, f"sv00001028sd0000{biosid}"):
                    self.passed(
                        f"Found platform meta package '{pmeta}' containing BIOS ID '{biosid}'"
                    )

        # Check ubuntu-drivers list
        stdout, returncode = self.run_command(["ubuntu-drivers", "list"])
        if returncode == 0:
            for line in stdout.split("\n"):
                if line.startswith("oem") and line.endswith("meta"):
                    pmeta = line.strip()
                    if self.has_modalias_match(pmeta, f"sv00001028sd0000{biosid}"):
                        self.passed(
                            f"Found platform meta package '{pmeta}' containing BIOS ID '{biosid}'"
                        )

    def check_somerville_focal_and_later(self, biosid: str) -> None:
        """Check Somerville meta packages for Focal/Jammy/Noble."""
        stdout, returncode = self.run_command(["ubuntu-drivers", "list"])
        if returncode != 0:
            return

        for line in stdout.split("\n"):
            if line.startswith("oem") and line.endswith("meta"):
                meta = line.strip()

                if not self.has_modalias_match(meta, f"sv00001028sd0000{biosid}"):
                    continue

                if not self.is_package_installed(meta):
                    continue

                # Construct factory package name
                factory = meta.replace("oem-somerville", "oem-somerville-factory")

                if self.is_package_installed(factory):
                    self.passed(
                        f"Found the platform meta package '{meta}' containing BIOS ID '{biosid}' "
                        f"and the platform factory meta package '{factory}'"
                    )

    def check_somerville_meta(self) -> None:
        """Check Somerville meta packages."""
        biosid, ubuntu_codename = self.prepare_somerville()

        if ubuntu_codename == "xenial":
            self.check_somerville_xenial(biosid)
        elif ubuntu_codename == "bionic":
            self.check_somerville_bionic(biosid)
        elif ubuntu_codename in ("focal", "jammy", "noble"):
            self.check_somerville_focal_and_later(biosid)
        else:
            self.failed(f"{ubuntu_codename} is not supported yet.")

        # Fall through to failure
        platform_info = (
            f"Platform Tag: {self.platform_tag}, " if self.platform_tag else ""
        )
        self.failed(f"{platform_info}BIOS ID: {biosid}")

    def run(self) -> None:
        """Run the appropriate check based on OEM codename."""
        if self.oem == "somerville":
            self.check_somerville_meta()
        elif self.oem in ("stella", "stella.cmit"):
            self.check_stella_meta()
        elif self.oem in ("sutton", "sutton.newell", "sutton.simon", "sutton.bachman"):
            self.check_sutton_meta()
        else:
            raise SystemExit(f"Unknown OEM codename: {self.oem}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test platform metapackage installation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--oem-codename",
        required=True,
        help="OEM codename (somerville, stella, stella.cmit, sutton, sutton.newell, sutton.simon, sutton.bachman)",
    )
    parser.add_argument("--platform-codename", help="Platform codename (optional)")

    args = parser.parse_args()

    print("Beginning Platform Metapackage Test", file=sys.stderr)

    test = PlatformMetaTest(args.oem_codename, args.platform_codename)
    test.run()


if __name__ == "__main__":
    main()
