#!/usr/bin/env python3
"""
Integration tests for platform_meta_test.py script.
Tests the Python implementation end-to-end with mocked system commands.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class PlatformMetaIntegrationTest(unittest.TestCase):
    """Base class for integration tests with helper methods."""
    
    script_path = None
    
    @classmethod
    def setUpClass(cls):
        """Find the Python script path."""
        if cls is PlatformMetaIntegrationTest:
            # Skip setup for base class
            return
        
        # Script is in ../bin directory relative to tests/
        base_path = Path(__file__).parent.parent / 'bin'
        cls.script_path = base_path / 'platform_meta_test.py'
        
        if not cls.script_path.exists():
            raise FileNotFoundError(f"Script not found: {cls.script_path}")
    
    def run_script(self, args, env=None, mock_commands=None):
        """
        Run the Python script with given arguments.
        
        Args:
            args: List of command-line arguments
            env: Environment variables to set
            mock_commands: Dict of command names to mock script contents
            
        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        # Create a temporary directory for mocks
        with tempfile.TemporaryDirectory() as tmpdir:
            test_env = os.environ.copy()
            
            # Set up PATH to include our mock commands
            if mock_commands:
                mock_bin = Path(tmpdir) / 'bin'
                mock_bin.mkdir()
                
                for cmd_name, cmd_script in mock_commands.items():
                    cmd_path = mock_bin / cmd_name
                    cmd_path.write_text(f"#!/bin/bash\n{cmd_script}\n")
                    cmd_path.chmod(0o755)
                
                test_env['PATH'] = f"{mock_bin}:{test_env['PATH']}"
            
            # Add custom environment variables
            if env:
                test_env.update(env)
            
            # Run the Python script
            cmd = ['python3', str(self.script_path)] + args
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=test_env
            )
            
            return result.stdout, result.stderr, result.returncode


class TestSomervilleXenial(PlatformMetaIntegrationTest):
    """Test Somerville project on Xenial."""
    
    def test_xenial_finds_dell_biosid_meta_package(self):
        """Should pass when dell-BIOSID-xenial-meta package is found."""
        biosid = '096E'
        
        mock_commands = {
            'dpkg': f'''
if [[ "$*" == "-l" ]]; then
    echo "ii  dell-{biosid}-xenial-meta  1.0  all  Dell meta"
    echo "ii  other-package  1.0  all  Other"
fi
''',
            'apt-cache': f'''
if [[ "$2" == "dell-{biosid}-xenial-meta" ]]; then
    echo "Depends: turis-vegas-mlk-glk-meta"
fi
''',
            'lsb_release': 'echo "xenial"',
            'cat': f'''
if [[ "$1" == *"product_sku"* ]]; then
    echo "{biosid}"
fi
'''
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'somerville'],
            mock_commands=mock_commands
        )
        
        self.assertEqual(returncode, 0, f"Script failed: {stdout}\n{stderr}")
        self.assertIn('passed', stdout.lower())
    
    def test_xenial_fails_without_matching_package(self):
        """Should fail when no matching dell-BIOSID-meta package exists."""
        mock_commands = {
            'dpkg': 'echo "ii  some-other-meta  1.0  all  Other"',
            'lsb_release': 'echo "xenial"',
            'cat': 'echo "096E"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'somerville'],
            mock_commands=mock_commands
        )
        
        self.assertNotEqual(returncode, 0, "Script should fail without matching package")
        self.assertIn('failed', stdout.lower())


class TestSomervilleFocal(PlatformMetaIntegrationTest):
    """Test Somerville project on Focal/Jammy/Noble."""
    
    def test_focal_finds_oem_meta_with_modaliases(self):
        """Should pass when oem-somerville meta with correct modaliases is found."""
        biosid = '096E'
        meta_pkg = 'oem-somerville.alder-whl-meta'
        factory_pkg = 'oem-somerville-factory.alder-whl-meta'
        
        mock_commands = {
            'ubuntu-drivers': f'''
if [[ "$1" == "list" ]]; then
    echo "{meta_pkg}"
    echo "{meta_pkg}-hwe"
fi
''',
            'apt-cache': f'''
if [[ "$2" == "{meta_pkg}" ]]; then
    echo "Modaliases: hwe(pci:*sv00001028sd0000{biosid}*)"
fi
''',
            'dpkg-query': f'''
if [[ "$*" == *"{meta_pkg}"* ]] || [[ "$*" == *"{factory_pkg}"* ]]; then
    echo "install ok installed"
fi
''',
            'lsb_release': 'echo "focal"',
            'cat': f'echo "{biosid}"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'somerville'],
            mock_commands=mock_commands
        )
        
        self.assertEqual(returncode, 0, f"Script failed: {stdout}\n{stderr}")
        self.assertIn('passed', stdout.lower())
        self.assertIn(meta_pkg, stdout)
        self.assertIn(factory_pkg, stdout)
    
    def test_focal_fails_when_factory_not_installed(self):
        """Should fail when platform meta is found but factory meta is not installed."""
        biosid = '096E'
        meta_pkg = 'oem-somerville.alder-whl-meta'
        factory_pkg = 'oem-somerville-factory.alder-whl-meta'
        
        mock_commands = {
            'ubuntu-drivers': f'echo "{meta_pkg}"',
            'apt-cache': f'echo "Modaliases: hwe(pci:*sv00001028sd0000{biosid}*)"',
            'dpkg-query': f'''
if [[ "$*" == *"{meta_pkg}"* ]]; then
    echo "install ok installed"
elif [[ "$*" == *"{factory_pkg}"* ]]; then
    echo "not installed"
    exit 1
fi
''',
            'lsb_release': 'echo "focal"',
            'cat': f'echo "{biosid}"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'somerville'],
            mock_commands=mock_commands
        )
        
        self.assertNotEqual(returncode, 0, "Script should fail when factory not installed")


class TestSuttonBachman(PlatformMetaIntegrationTest):
    """Test Sutton Bachman project."""
    
    def test_sutton_passes_with_4_meta_packages(self):
        """Should pass when exactly 4 meta packages are found with correct BIOS ID."""
        biosid = 'A12'
        oem = 'sutton.bachman'
        platform = 'baara'
        
        mock_commands = {
            'dpkg-query': f'''
if [[ "$*" == *"-f="* ]]; then
    # Return package list
    echo "oem-{oem}-factory-meta"
    echo "oem-{oem}-meta"
    echo "oem-{oem}-{platform}-meta"
    echo "oem-{oem}-factory-{platform}-meta"
fi
if [[ "$*" == *"Status"* ]]; then
    echo "install ok installed"
fi
''',
            'apt-cache': f'''
if [[ "$2" == "oem-{oem}-{platform}-meta" ]]; then
    echo "Modaliases: dmi(bvr{biosid}*)"
fi
''',
            'cat': f'''
if [[ "$1" == *"bios_version"* ]]; then
    echo "{biosid}.B456.C789"
fi
'''
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'sutton.bachman'],
            mock_commands=mock_commands
        )
        
        self.assertEqual(returncode, 0, f"Script failed: {stdout}\n{stderr}")
        self.assertIn('passed', stdout.lower())
        self.assertIn(biosid, stdout)
    
    def test_sutton_fails_with_too_few_packages(self):
        """Should fail when less than 4 meta packages are found."""
        mock_commands = {
            'dpkg-query': '''
if [[ "$*" == *"-f="* ]]; then
    echo "oem-sutton.bachman-meta"
    echo "oem-sutton.bachman-baara-meta"
fi
''',
            'cat': 'echo "A12.B456.C789"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'sutton.bachman'],
            mock_commands=mock_commands
        )
        
        self.assertNotEqual(returncode, 0, "Script should fail with < 4 packages")
        self.assertIn('missing', stdout.lower())
    
    def test_sutton_fails_with_too_many_packages(self):
        """Should fail when more than 4 meta packages are found."""
        mock_commands = {
            'dpkg-query': '''
if [[ "$*" == *"-f="* ]]; then
    echo "oem-sutton.bachman-meta"
    echo "oem-sutton.bachman-factory-meta"
    echo "oem-sutton.bachman-baara-meta"
    echo "oem-sutton.bachman-factory-baara-meta"
    echo "oem-sutton.bachman-extra-meta"
fi
''',
            'cat': 'echo "A12.B456.C789"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'sutton.bachman'],
            mock_commands=mock_commands
        )
        
        self.assertNotEqual(returncode, 0, "Script should fail with > 4 packages")
        self.assertIn('too many', stdout.lower())
    
    def test_sutton_fails_when_biosid_mismatch(self):
        """Should fail when meta package doesn't match BIOS ID."""
        biosid = 'A12'
        wrong_biosid = 'B99'
        
        mock_commands = {
            'dpkg-query': '''
echo "oem-sutton.bachman-factory-meta"
echo "oem-sutton.bachman-meta"
echo "oem-sutton.bachman-baara-meta"
echo "oem-sutton.bachman-factory-baara-meta"
''',
            'apt-cache': f'echo "Modaliases: dmi(bvr{wrong_biosid}*)"',
            'cat': f'echo "{biosid}.B456.C789"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'sutton.bachman'],
            mock_commands=mock_commands
        )
        
        self.assertNotEqual(returncode, 0, "Script should fail on BIOS ID mismatch")
        self.assertIn('doesnt match', stdout.lower())


class TestStellaCmit(PlatformMetaIntegrationTest):
    """Test Stella CMIT project."""
    
    def test_stella_not_supported(self):
        """Should exit 0 but indicate stella is not supported."""
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'stella']
        )
        
        self.assertEqual(returncode, 0, "stella should exit 0")
        self.assertIn('not support', stdout.lower())
    
    def test_stella_cmit_not_supported(self):
        """Should exit 0 but indicate stella.cmit is not supported."""
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'stella.cmit']
        )
        
        self.assertEqual(returncode, 0, "stella.cmit should exit 0")
        self.assertIn('not support', stdout.lower())


class TestSuttonVariants(PlatformMetaIntegrationTest):
    """Test Sutton project variants."""
    
    def test_sutton_passes_with_4_meta_packages(self):
        """Plain 'sutton' should work with 4 meta packages."""
        biosid = 'X99'
        
        mock_commands = {
            'dpkg-query': '''
echo "oem-sutton-factory-meta"
echo "oem-sutton-meta"
echo "oem-sutton-platform-meta"
echo "oem-sutton-factory-platform-meta"
if [[ "$*" == *"Status"* ]]; then
    echo "install ok installed"
fi
''',
            'apt-cache': f'echo "Modaliases: dmi(bvr{biosid}*)"',
            'cat': f'echo "{biosid}.B456.C789"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'sutton'],
            mock_commands=mock_commands
        )
        
        self.assertEqual(returncode, 0, f"'sutton' should work: {stdout}\n{stderr}")
    
    def test_sutton_bachman_variant_passes(self):
        """'sutton.bachman' variant should work with 4 meta packages."""
        biosid = 'B99'
        
        mock_commands = {
            'dpkg-query': '''
echo "oem-sutton.bachman-factory-meta"
echo "oem-sutton.bachman-meta"
echo "oem-sutton.bachman-baara-meta"
echo "oem-sutton.bachman-factory-baara-meta"
if [[ "$*" == *"Status"* ]]; then
    echo "install ok installed"
fi
''',
            'apt-cache': f'echo "Modaliases: dmi(bvr{biosid}*)"',
            'cat': f'echo "{biosid}.B456.C789"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'sutton.bachman'],
            mock_commands=mock_commands
        )
        
        self.assertEqual(returncode, 0, f"'sutton.bachman' should work: {stdout}\n{stderr}")


class TestArgumentParsing(PlatformMetaIntegrationTest):
    """Test command-line argument parsing."""
    
    def test_help_option(self):
        """Should display help and exit 0."""
        stdout, stderr, returncode = self.run_script(['--help'])
        
        self.assertEqual(returncode, 0)
        output = stdout + stderr
        self.assertIn('usage', output.lower())
        self.assertIn('oem-codename', output.lower())
    
    def test_missing_oem_codename(self):
        """Should fail when no --oem-codename provided."""
        stdout, stderr, returncode = self.run_script([])
        
        self.assertNotEqual(returncode, 0)
        output = stdout + stderr
        self.assertIn('usage', output.lower() if output else '')
    
    def test_invalid_oem_codename(self):
        """Should show usage for invalid OEM codename."""
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'invalid-oem']
        )
        
        self.assertNotEqual(returncode, 0)


class TestCaseInsensitivity(PlatformMetaIntegrationTest):
    """Test case-insensitive matching behavior."""
    
    def test_sutton_biosid_case_insensitive(self):
        """Should match BIOS ID case-insensitively."""
        biosid = 'A12'
        
        mock_commands = {
            'dpkg-query': '''
echo "oem-sutton.bachman-factory-meta"
echo "oem-sutton.bachman-meta"
echo "oem-sutton.bachman-baara-meta"
echo "oem-sutton.bachman-factory-baara-meta"
if [[ "$*" == *"Status"* ]]; then
    echo "install ok installed"
fi
''',
            # Return lowercase in modaliases
            'apt-cache': 'echo "Modaliases: dmi(bvra12*)"',
            'cat': f'echo "{biosid}.B456.C789"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'sutton.bachman'],
            mock_commands=mock_commands
        )
        
        self.assertEqual(returncode, 0, f"Should match case-insensitively: {stdout}")
    
    def test_somerville_biosid_case_insensitive(self):
        """Should match Somerville BIOS ID case-insensitively."""
        biosid = '096E'
        
        mock_commands = {
            'ubuntu-drivers': 'echo "oem-somerville.alder-whl-meta"',
            # Return with different case
            'apt-cache': f'echo "Modaliases: hwe(pci:*sv00001028sd0000{biosid.lower()}*)"',
            'dpkg-query': 'echo "install ok installed"',
            'lsb_release': 'echo "focal"',
            'cat': f'echo "{biosid}"'
        }
        
        stdout, stderr, returncode = self.run_script(
            ['--oem-codename', 'somerville'],
            mock_commands=mock_commands
        )
        
        self.assertEqual(returncode, 0, f"Should match case-insensitively: {stdout}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
