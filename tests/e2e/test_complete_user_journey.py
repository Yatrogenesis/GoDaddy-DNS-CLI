"""
End-to-End Tests: Complete User Journey
Tests the actual user experience from fresh installation to DNS management
NO MOCKS - Real subprocess calls to test the complete CLI experience
"""

import pytest
import subprocess
import tempfile
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
import time

# Skip E2E tests unless explicitly requested
pytestmark = pytest.mark.skipif(
    not os.getenv('RUN_E2E_TESTS', '').lower() in ('1', 'true', 'yes'),
    reason="E2E tests require RUN_E2E_TESTS=1 environment variable"
)


class TestCompleteUserJourney:
    """
    Test the complete user journey as they would experience it:
    1. Fresh installation
    2. Configuration setup
    3. Authentication
    4. Basic DNS operations

    This simulates what happens when a user follows the README instructions
    """

    @classmethod
    def setup_class(cls):
        """Setup for E2E tests"""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="godaddy_e2e_"))
        cls.config_file = cls.test_dir / "test_config.json"

        # Check if we have test credentials
        cls.api_key = os.getenv('GODADDY_TEST_API_KEY')
        cls.api_secret = os.getenv('GODADDY_TEST_API_SECRET')
        cls.test_domain = os.getenv('GODADDY_TEST_DOMAIN', 'example.com')

        if not cls.api_key or not cls.api_secret:
            pytest.skip("E2E tests require GODADDY_TEST_API_KEY and GODADDY_TEST_API_SECRET")

    @classmethod
    def teardown_class(cls):
        """Cleanup after E2E tests"""
        import shutil
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def run_cli_command(self, args: list, input_text: str = None, expect_failure: bool = False) -> Dict[str, Any]:
        """
        Run CLI command and return structured result
        This simulates exactly what a user would type in their terminal
        """
        # Use the installed CLI or development version
        cmd = [sys.executable, '-m', 'godaddy_cli.cli'] + args + ['--config-file', str(self.config_file)]

        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=30,
                cwd=self.test_dir
            )

            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0,
                'cmd': ' '.join(cmd)
            }

        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out',
                'success': False,
                'cmd': ' '.join(cmd)
            }

    def test_01_fresh_installation_help(self):
        """Test: User runs --help on fresh installation"""
        result = self.run_cli_command(['--help'])

        assert result['success'], f"Help command failed: {result['stderr']}"
        assert 'GoDaddy DNS CLI' in result['stdout'], "CLI banner not found in help"
        assert 'dns' in result['stdout'], "DNS command not listed in help"
        assert 'auth' in result['stdout'], "Auth command not listed in help"

    def test_02_configuration_setup_interactive(self):
        """Test: User sets up configuration (simulating interactive input)"""
        # Simulate interactive auth setup
        input_text = f"{self.api_key}\n{self.api_secret}\ny\n"

        result = self.run_cli_command(['auth', 'setup'], input_text=input_text)

        # Should succeed or at least create config structure
        assert self.config_file.exists(), "Config file was not created"

        # Verify config file structure
        if self.config_file.exists():
            config_data = json.loads(self.config_file.read_text())
            assert 'profiles' in config_data, "Config missing profiles section"
            assert 'default' in config_data['profiles'], "Config missing default profile"

    def test_03_authentication_test(self):
        """Test: User tests API connection"""
        result = self.run_cli_command(['auth', 'test'])

        # This should either succeed or fail gracefully with helpful message
        if not result['success']:
            # Check that we get a helpful error message, not a stack trace
            assert 'API' in result['stderr'] or 'connection' in result['stderr'], \
                f"Unhelpful error message: {result['stderr']}"
        else:
            assert 'success' in result['stdout'].lower() or 'connected' in result['stdout'].lower(), \
                "Success message not clear"

    def test_04_status_command_workflow(self):
        """Test: User checks system status"""
        result = self.run_cli_command(['status'])

        assert result['success'], f"Status command failed: {result['stderr']}"
        assert 'Configuration Status' in result['stdout'], "Status output missing expected content"
        assert 'Profile' in result['stdout'], "Status missing profile information"

    def test_05_domain_listing_workflow(self):
        """Test: User lists their domains"""
        result = self.run_cli_command(['domains', 'list'])

        if result['success']:
            # If successful, should show domains or empty message
            assert len(result['stdout']) > 0, "Domain list produced no output"
        else:
            # If failed, should give helpful error
            assert 'API' in result['stderr'] or 'credential' in result['stderr'], \
                f"Domain list error not helpful: {result['stderr']}"

    def test_06_dns_records_listing_workflow(self):
        """Test: User lists DNS records for a domain"""
        result = self.run_cli_command(['dns', 'list', self.test_domain])

        if result['success']:
            # Should show records or "no records found"
            assert len(result['stdout']) > 0, "DNS list produced no output"
        else:
            # Should give helpful error about domain or credentials
            error_text = result['stderr'].lower()
            helpful_keywords = ['domain', 'not found', 'credential', 'api', 'permission']
            assert any(keyword in error_text for keyword in helpful_keywords), \
                f"DNS list error not helpful: {result['stderr']}"

    def test_07_dns_validation_workflow(self):
        """Test: User validates DNS configuration"""
        result = self.run_cli_command(['dns', 'validate', self.test_domain])

        # Validation should work or give clear error
        if not result['success']:
            assert 'domain' in result['stderr'].lower() or 'api' in result['stderr'].lower(), \
                f"Validation error not helpful: {result['stderr']}"

    def test_08_bulk_export_workflow(self):
        """Test: User exports DNS records"""
        export_file = self.test_dir / "test_export.csv"

        result = self.run_cli_command([
            'bulk', 'export', self.test_domain,
            '--format', 'csv',
            '--output', str(export_file)
        ])

        if result['success']:
            assert export_file.exists(), "Export file was not created"
            content = export_file.read_text()
            assert 'name,type,data' in content.lower(), "Export file missing CSV headers"
        else:
            # Should give helpful error
            assert len(result['stderr']) > 0, "Export command failed silently"

    def test_09_error_handling_quality(self):
        """Test: Error messages are helpful, not technical"""
        # Try to access non-existent domain
        result = self.run_cli_command(['dns', 'list', 'definitely-not-a-real-domain-12345.com'])

        assert not result['success'], "Should fail for non-existent domain"

        # Error should be user-friendly, not a stack trace
        error_text = result['stderr']
        assert 'Traceback' not in error_text, "Error message contains stack trace"
        assert len(error_text) > 10, "Error message too short to be helpful"

        # Should suggest what to do
        helpful_phrases = ['check', 'verify', 'try', 'make sure', 'ensure']
        assert any(phrase in error_text.lower() for phrase in helpful_phrases), \
            f"Error message not helpful: {error_text}"

    def test_10_json_output_workflow(self):
        """Test: User requests JSON output"""
        result = self.run_cli_command(['--json', 'domains', 'list'])

        if result['success']:
            try:
                # Should be valid JSON
                json.loads(result['stdout'])
            except json.JSONDecodeError:
                pytest.fail(f"JSON output is invalid: {result['stdout']}")

    def test_11_command_chaining_workflow(self):
        """Test: Multiple commands work in sequence (realistic user session)"""
        commands = [
            (['status'], "Check status"),
            (['domains', 'list'], "List domains"),
            (['auth', 'test'], "Test authentication")
        ]

        results = []
        for cmd_args, description in commands:
            result = self.run_cli_command(cmd_args)
            results.append((description, result['success'], result.get('stderr', '')))

        # At least status should work
        status_success = results[0][1]
        assert status_success, f"Basic status command failed: {results[0][2]}"

    def test_12_help_system_completeness(self):
        """Test: Help system provides complete guidance"""
        # Test help for main command groups
        help_commands = [
            ['dns', '--help'],
            ['auth', '--help'],
            ['domains', '--help'],
            ['bulk', '--help']
        ]

        for cmd in help_commands:
            result = self.run_cli_command(cmd)
            assert result['success'], f"Help failed for {cmd}: {result['stderr']}"

            # Help should contain examples or usage patterns
            help_text = result['stdout'].lower()
            help_indicators = ['usage:', 'example', 'options:', 'commands:']
            assert any(indicator in help_text for indicator in help_indicators), \
                f"Help for {cmd} lacks proper structure"

    def test_13_configuration_persistence(self):
        """Test: Configuration persists between command runs"""
        # Run two commands that both need config
        result1 = self.run_cli_command(['status'])
        result2 = self.run_cli_command(['status'])

        # Both should have consistent behavior
        assert result1['success'] == result2['success'], \
            "Configuration not persistent between runs"

    def test_14_real_world_error_scenarios(self):
        """Test: Common real-world error scenarios are handled gracefully"""
        error_scenarios = [
            # Invalid domain format
            (['dns', 'list', 'not-a-domain'], "Invalid domain format"),
            # Missing required arguments
            (['dns', 'add'], "Missing required arguments"),
            # Invalid record type
            (['dns', 'add', self.test_domain, '--type', 'INVALID', '--name', 'test', '--data', '1.1.1.1'], "Invalid record type")
        ]

        for cmd_args, description in error_scenarios:
            result = self.run_cli_command(cmd_args)

            # Should fail gracefully
            assert not result['success'], f"Command should have failed: {description}"

            # Error should be helpful
            assert len(result['stderr']) > 0, f"No error message for: {description}"
            assert 'Traceback' not in result['stderr'], f"Stack trace in error: {description}"

    def test_15_performance_reasonable(self):
        """Test: Commands complete in reasonable time"""
        start_time = time.time()
        result = self.run_cli_command(['--help'])
        duration = time.time() - start_time

        assert duration < 5.0, f"Help command took too long: {duration:.2f}s"
        assert result['success'], "Help command failed"


class TestE2EUserScenarios:
    """Test complete user scenarios that mirror real-world usage"""

    def test_new_user_onboarding_scenario(self):
        """
        Scenario: Complete new user onboarding
        User has never used the tool, follows README instructions
        """
        # This would be a complete scenario test
        # For now, we'll implement the structure
        pass

    def test_daily_dns_management_scenario(self):
        """
        Scenario: Daily DNS management tasks
        User regularly updates DNS records for their domains
        """
        pass

    def test_bulk_migration_scenario(self):
        """
        Scenario: Bulk DNS migration
        User migrates DNS records from another provider
        """
        pass


# Helper function to run E2E tests manually
def run_e2e_tests_manual():
    """
    Manual E2E test runner for development
    Usage: python -c "from tests.e2e.test_complete_user_journey import run_e2e_tests_manual; run_e2e_tests_manual()"
    """
    os.environ['RUN_E2E_TESTS'] = '1'

    # Run with pytest
    import subprocess
    result = subprocess.run([
        'python', '-m', 'pytest',
        'tests/e2e/',
        '-v',
        '--tb=short'
    ])

    return result.returncode


if __name__ == '__main__':
    run_e2e_tests_manual()