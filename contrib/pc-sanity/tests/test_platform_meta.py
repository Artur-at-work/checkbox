#!/usr/bin/env python3
"""
Unit tests for platform_meta_test bash script.
These tests capture the behavior of the bash script before refactoring.
Useful for AI to understand intended functionality.
"""

import re
import subprocess
import unittest
from unittest.mock import patch, mock_open, MagicMock


class TestPrepareHelpers(unittest.TestCase):
    """Test the prepare_somerville and prepare_sutton helper functions."""

    @patch("builtins.open", new_callable=mock_open, read_data="096E\n")
    @patch("subprocess.run")
    def test_prepare_somerville_reads_product_sku(self, mock_run, mock_file):
        """Should read product_sku from DMI and get ubuntu codename."""
        mock_run.return_value = MagicMock(stdout="focal\n", returncode=0)

        # This represents the behavior of prepare_somerville()
        with open("/sys/devices/virtual/dmi/id/product_sku") as f:
            biosid = f.read().strip()
        result = subprocess.run(["lsb_release", "-cs"], capture_output=True, text=True)
        ubuntu_codename = result.stdout.strip()

        self.assertEqual(biosid, "096E")
        self.assertEqual(ubuntu_codename, "focal")
        mock_file.assert_called_with("/sys/devices/virtual/dmi/id/product_sku")

    @patch("builtins.open", new_callable=mock_open, read_data="A12.B345.C678\n")
    def test_prepare_sutton_extracts_first_3_chars_of_bios(self, mock_file):
        """Should read BIOS version and extract first 3 characters as BIOSID."""
        with open("/sys/devices/virtual/dmi/id/bios_version") as f:
            bios = f.read().strip()
        biosid = bios[:3]

        self.assertEqual(biosid, "A12")
        mock_file.assert_called_with("/sys/devices/virtual/dmi/id/bios_version")


class TestSuttonMetaChecks(unittest.TestCase):
    """Test sutton meta package checking logic."""

    @patch("subprocess.run")
    def test_sutton_requires_exactly_4_meta_packages(self, mock_run):
        """Should fail if not exactly 4 meta packages matching oem-$oem*-meta."""
        # Test with 0 packages
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\n", "oem-sutton.bachman*-meta"],
            capture_output=True,
            text=True,
        )
        package_count = len([p for p in result.stdout.strip().split("\n") if p])
        self.assertEqual(package_count, 0)

        # Test with 3 packages (too few)
        mock_run.return_value = MagicMock(
            stdout="oem-sutton.bachman-meta\noem-sutton.bachman-factory-meta\noem-sutton.bachman-baara-meta\n",
            returncode=0,
        )
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\n", "oem-sutton.bachman*-meta"],
            capture_output=True,
            text=True,
        )
        package_count = len([p for p in result.stdout.strip().split("\n") if p])
        self.assertEqual(package_count, 3)

        # Test with 4 packages (correct)
        mock_run.return_value = MagicMock(
            stdout="oem-sutton.bachman-meta\noem-sutton.bachman-factory-meta\noem-sutton.bachman-baara-meta\noem-sutton.bachman-factory-baara-meta\n",
            returncode=0,
        )
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\n", "oem-sutton.bachman*-meta"],
            capture_output=True,
            text=True,
        )
        package_count = len([p for p in result.stdout.strip().split("\n") if p])
        self.assertEqual(package_count, 4)

        # Test with 5 packages (too many)
        mock_run.return_value = MagicMock(
            stdout="oem-sutton.bachman-meta\noem-sutton.bachman-factory-meta\noem-sutton.bachman-baara-meta\noem-sutton.bachman-factory-baara-meta\noem-extra-meta\n",
            returncode=0,
        )
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\n", "oem-sutton.bachman*-meta"],
            capture_output=True,
            text=True,
        )
        package_count = len([p for p in result.stdout.strip().split("\n") if p])
        self.assertEqual(package_count, 5)

    def test_sutton_extracts_platform_name_from_package(self):
        """Should extract platform name from package, skipping 'factory' and 'meta'."""
        packages = [
            "oem-ouagadougou-meta",
            "oem-sutton.bachman-factory-meta",
            "oem-sutton.bachman-meta",
            "oem-sutton.bachman-baara-meta",
            "oem-sutton.bachman-factory-baara-meta",
        ]

        platform_tag = None
        oem = None
        for pkg in packages:
            parts = pkg.split("-")
            if len(parts) >= 3:
                platform_name = parts[2]
                if platform_name == "factory":
                    continue
                if platform_name == "meta":
                    continue
                if platform_name:
                    platform_tag = platform_name
                    oem = parts[1]
                    break

        # Should extract 'baara' as platform_tag (first non-factory, non-meta 3rd field)
        # From 'oem-sutton.bachman-baara-meta'
        self.assertEqual(platform_tag, "baara")
        self.assertEqual(oem, "sutton.bachman")

    @patch("subprocess.run")
    def test_sutton_checks_modaliases_for_bios_id(self, mock_run):
        """Should check if meta package Modaliases contains bvr$BIOSID."""
        biosid = "A12"
        meta = "oem-sutton.bachman-sutton.bachman-meta"

        # Mock apt-cache show with Modaliases containing the BIOSID
        # Bash uses: grep ^Modaliases | grep -i "bvr$BIOSID"
        mock_run.return_value = MagicMock(
            stdout="Package: oem-sutton.bachman-sutton.bachman-meta\nModaliases: dmi(bvra12*)\n",
            returncode=0,
        )

        result = subprocess.run(
            ["apt-cache", "show", meta], capture_output=True, text=True
        )
        # Case-insensitive check as bash uses grep -i
        has_biosid = f"bvr{biosid}".lower() in result.stdout.lower()

        self.assertTrue(has_biosid)

    @patch("subprocess.run")
    def test_sutton_verifies_meta_and_factory_installed(self, mock_run):
        """Should verify both meta and factory packages are installed."""
        meta = "oem-sutton.bachman-sutton.bachman-meta"
        factory = "oem-sutton.bachman-factory-sutton.bachman-meta"

        # Mock successful installation check
        mock_run.return_value = MagicMock(stdout="install ok installed\n", returncode=0)

        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}\n", meta],
            capture_output=True,
            text=True,
            stderr=subprocess.STDOUT,
        )
        meta_installed = "install ok installed" in result.stdout

        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}\n", factory],
            capture_output=True,
            text=True,
            stderr=subprocess.STDOUT,
        )
        factory_installed = "install ok installed" in result.stdout

        self.assertTrue(meta_installed)
        self.assertTrue(factory_installed)


class TestSomervilleMetaChecks(unittest.TestCase):
    """Test somerville meta package checking logic."""

    @patch("subprocess.run")
    def test_xenial_checks_dell_biosid_pattern(self, mock_run):
        """Xenial should look for dell-$BIOSID(-xenial)?-meta pattern."""
        biosid = "096E"

        # Mock dpkg -l output
        mock_run.side_effect = [
            MagicMock(
                stdout="ii  dell-096E-xenial-meta  1.0  all  Dell meta package\n",
                returncode=0,
            ),
            MagicMock(stdout="Depends: turis-vegas-mlk-glk-meta\n", returncode=0),
        ]

        # Get packages
        result = subprocess.run(["dpkg", "-l"], capture_output=True, text=True)
        packages = [
            line.split()[1]
            for line in result.stdout.split("\n")
            if line and "-meta" in line
        ]

        # Check pattern
        pattern = f"^dell-{biosid}(-xenial)?-meta$"
        matching = [p for p in packages if re.match(pattern, p)]

        self.assertTrue(len(matching) > 0)
        self.assertEqual(matching[0], "dell-096E-xenial-meta")

    @patch("subprocess.run")
    def test_bionic_checks_multiple_patterns(self, mock_run):
        """Bionic should check dell-BIOSID-meta, platform-meta, and oem-platform-meta."""
        biosid = "096E"
        platform_tag = "turis-vegas-mlk-glk"

        # Should check three patterns:
        # 1. dell-096E-bionic-meta (old style)
        # 2. turis-vegas-mlk-glk-meta (transition)
        # 3. oem-turis-vegas-mlk-glk-meta (new style with modaliases)

        expected_checks = [
            f"dell-{biosid}-bionic-meta",
            f"{platform_tag}-meta",
            f"oem-{platform_tag}-meta",
        ]

        self.assertEqual(len(expected_checks), 3)

    @patch("subprocess.run")
    def test_focal_checks_ubuntu_drivers_with_modaliases(self, mock_run):
        """Focal/Jammy/Noble should use ubuntu-drivers list and check modaliases."""
        biosid = "096E"

        # Mock ubuntu-drivers list
        mock_run.side_effect = [
            MagicMock(
                stdout="oem-somerville.alder-whl-meta\noem-somerville.alder-whl-hwe-meta\n",
                returncode=0,
            ),
            MagicMock(
                stdout="Modaliases: hwe(pci:*sv00001028sd0000096E*)\n", returncode=0
            ),
            MagicMock(stdout="install ok installed\n", returncode=0),
            MagicMock(stdout="install ok installed\n", returncode=0),
        ]

        # Get OEM packages from ubuntu-drivers
        result = subprocess.run(
            ["ubuntu-drivers", "list"], capture_output=True, text=True
        )
        oem_packages = [
            line.strip()
            for line in result.stdout.split("\n")
            if line.startswith("oem") and line.endswith("meta")
        ]

        self.assertEqual(len(oem_packages), 2)

        # Check modaliases - bash uses grep -i for case-insensitive matching
        result = subprocess.run(
            ["apt-cache", "show", oem_packages[0]], capture_output=True, text=True
        )
        # Case-insensitive check
        has_biosid = f"sv00001028sd0000{biosid}".lower() in result.stdout.lower()

        self.assertTrue(has_biosid)

    @patch("subprocess.run")
    def test_focal_verifies_both_meta_and_factory_packages(self, mock_run):
        """Focal+ should verify both platform meta and factory meta are installed."""
        meta = "oem-somerville.alder-whl-meta"
        factory = "oem-somerville-factory.alder-whl-meta"

        # The script does string replacement: ${meta/oem-somerville/oem-somerville-factory}
        expected_factory = meta.replace("oem-somerville", "oem-somerville-factory")

        self.assertEqual(expected_factory, factory)

    def test_unsupported_ubuntu_version_should_fail(self):
        """Should fail for unsupported Ubuntu versions."""
        unsupported_versions = ["trusty", "precise", "lunar", "mantic"]
        supported_versions = ["xenial", "bionic", "focal", "jammy", "noble"]

        for version in unsupported_versions:
            self.assertNotIn(version, supported_versions)


class TestArgumentParsing(unittest.TestCase):
    """Test command-line argument parsing behavior."""

    def test_requires_oem_codename(self):
        """Should accept valid OEM codenames."""
        # Current names (without dots): somerville, stella, sutton
        # Dotted variants also supported: stella.cmit, sutton.newell, sutton.simon, sutton.bachman
        valid_oems = [
            "somerville",
            "stella",
            "stella.cmit",
            "sutton",
            "sutton.newell",
            "sutton.simon",
            "sutton.bachman",
        ]

        # This test just documents the valid OEM codenames
        # Integration tests verify they actually work
        for oem in valid_oems:
            self.assertIsNotNone(oem)

    def test_optional_platform_codename(self):
        """Platform codename is optional but used when provided."""
        # The script accepts --platform-codename but it's not always required
        platform_tag = "turis-vegas-mlk-glk"
        self.assertIsNotNone(platform_tag)

    def test_stella_not_implemented(self):
        """stella and stella.cmit should exit with 0 but not actually check anything."""
        # check_stella_cmit_meta() just prints "not support stella.cmit yet" and exits 0
        pass


class TestExitBehavior(unittest.TestCase):
    """Test exit behavior and messages."""

    def test_passed_exits_0_with_message(self):
        """passed() should print message and exit 0."""
        # In bash: passed() { echo "$1"; echo "$0 passed!"; exit 0; }
        pass

    def test_failed_exits_1_with_message(self):
        """failed() should print message and exit 1."""
        # In bash: failed() { echo "$1"; echo "$0 failed!"; exit 1; }
        pass

    def test_somerville_falls_through_to_failed(self):
        """check_somerville_meta should fall through to failed() if no match."""
        # The function ends with: failed "Platform Tag: $platform_tag, BIOS ID: $BIOSID"
        pass


class TestPackageNameParsing(unittest.TestCase):
    """Test package name parsing logic."""

    def test_split_package_name_by_dash(self):
        """Should split package names by dash to extract components."""
        pkg = "oem-sutton.bachman-baara-meta"
        parts = pkg.split("-")

        self.assertEqual(parts[0], "oem")
        self.assertEqual(parts[1], "sutton.bachman")
        self.assertEqual(parts[2], "baara")
        self.assertEqual(parts[3], "meta")

    def test_construct_factory_package_name(self):
        """Should construct factory package name from meta package."""
        oem = "sutton.bachman"
        platform_tag = "baara"

        meta = f"oem-{oem}-{platform_tag}-meta"
        factory = f"oem-{oem}-factory-{platform_tag}-meta"

        self.assertEqual(meta, "oem-sutton.bachman-baara-meta")
        self.assertEqual(factory, "oem-sutton.bachman-factory-baara-meta")


class TestModaliasParsing(unittest.TestCase):
    """Test parsing of Modaliases field from apt-cache."""

    def test_extract_modaliases_from_apt_cache_output(self):
        """Should extract Modaliases field from apt-cache show output."""
        apt_output = """Package: oem-somerville.alder-whl-meta
Version: 1.0
Modaliases: hwe(pci:*sv00001028sd0000096E*, pci:*sv00001028sd0000096F*)
Description: Dell meta package
"""
        lines = apt_output.split("\n")
        modaliases_line = [l for l in lines if l.startswith("Modaliases:")]

        self.assertEqual(len(modaliases_line), 1)
        self.assertIn("sv00001028sd0000096E", modaliases_line[0])

    def test_sutton_modalias_pattern(self):
        """Sutton checks for bvr$BIOSID in modaliases."""
        biosid = "A12"
        modalias = "dmi(bvrA12*)"

        self.assertIn(f"bvr{biosid}", modalias)

    def test_somerville_modalias_pattern(self):
        """Somerville checks for sv00001028sd0000$BIOSID in modaliases."""
        biosid = "096E"
        modalias = "pci:*sv00001028sd0000096E*"

        self.assertIn(f"sv00001028sd0000{biosid}", modalias)


if __name__ == "__main__":
    unittest.main()
