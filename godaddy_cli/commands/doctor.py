"""
System Health Diagnostics Command
A comprehensive health check for the GoDaddy DNS CLI system
"""

import click
import sys
import os
import json
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from godaddy_cli.core.config import ConfigManager
from godaddy_cli.core.auth import AuthManager
from godaddy_cli.core.simple_api_client import APIClient
from godaddy_cli.utils.formatters import format_status_panel

console = Console()


@click.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed diagnostic information')
@click.option('--fix', is_flag=True, help='Attempt to fix common issues automatically')
@click.option('--export', type=click.Path(), help='Export diagnostic report to file')
@click.pass_context
def doctor(ctx, verbose, fix, export):
    """
    🩺 System Health Diagnostics

    Performs comprehensive health checks on your GoDaddy DNS CLI installation:
    • Configuration validation
    • API connectivity testing
    • Credential verification
    • Environment checks
    • Performance diagnostics

    This command helps identify and resolve common issues before they affect your workflow.

    Examples:
        godaddy doctor                    # Basic health check
        godaddy doctor --verbose          # Detailed diagnostics
        godaddy doctor --fix             # Auto-fix common issues
        godaddy doctor --export report.json  # Save diagnostics
    """
    diagnostics = SystemDiagnostics(ctx.obj.get('config'), ctx.obj.get('auth'))

    console.print(Panel(
        "[bold cyan]GoDaddy DNS CLI System Diagnostics[/bold cyan]\n"
        "[dim]Checking system health and identifying potential issues...[/dim]",
        border_style="cyan"
    ))

    # Run all diagnostic checks
    results = diagnostics.run_all_checks(verbose=verbose, auto_fix=fix)

    # Display results
    diagnostics.display_results(results, verbose=verbose)

    # Export if requested
    if export:
        diagnostics.export_report(results, export)
        console.print(f"\n[green]Diagnostic report exported to: {export}[/green]")

    # Exit with appropriate code
    if results['overall_health'] == 'critical':
        sys.exit(1)
    elif results['overall_health'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)


class SystemDiagnostics:
    """Comprehensive system diagnostics for GoDaddy DNS CLI"""

    def __init__(self, config_manager: ConfigManager = None, auth_manager: AuthManager = None):
        self.config = config_manager
        self.auth = auth_manager
        self.checks = []

    def run_all_checks(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Run all diagnostic checks and return comprehensive results"""
        results = {
            'timestamp': self._get_timestamp(),
            'system_info': self._get_system_info(),
            'checks': {},
            'issues': [],
            'warnings': [],
            'fixes_applied': [],
            'overall_health': 'healthy'
        }

        # Define all diagnostic checks
        checks = [
            ('python_environment', self._check_python_environment),
            ('package_installation', self._check_package_installation),
            ('configuration_files', self._check_configuration_files),
            ('credentials_security', self._check_credentials_security),
            ('api_connectivity', self._check_api_connectivity),
            ('permissions', self._check_file_permissions),
            ('dependencies', self._check_dependencies),
            ('performance', self._check_performance),
            ('disk_space', self._check_disk_space),
            ('network_connectivity', self._check_network_connectivity)
        ]

        # Run each check
        for check_name, check_func in checks:
            try:
                console.print(f"[cyan]Checking {check_name.replace('_', ' ')}...[/cyan]")
                check_result = check_func(verbose=verbose, auto_fix=auto_fix)
                results['checks'][check_name] = check_result

                if check_result['status'] == 'error':
                    results['issues'].extend(check_result.get('issues', []))
                elif check_result['status'] == 'warning':
                    results['warnings'].extend(check_result.get('warnings', []))

                if check_result.get('fixes_applied'):
                    results['fixes_applied'].extend(check_result['fixes_applied'])

            except Exception as e:
                results['checks'][check_name] = {
                    'status': 'error',
                    'message': f'Check failed: {str(e)}',
                    'issues': [f'Diagnostic check "{check_name}" crashed: {str(e)}']
                }
                results['issues'].append(f'Diagnostic check "{check_name}" crashed: {str(e)}')

        # Determine overall health
        if results['issues']:
            results['overall_health'] = 'critical'
        elif results['warnings']:
            results['overall_health'] = 'warning'
        else:
            results['overall_health'] = 'healthy'

        return results

    def _check_python_environment(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check Python version and environment"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        # Check Python version
        python_version = platform.python_version()
        result['details']['python_version'] = python_version

        major, minor = map(int, python_version.split('.')[:2])
        if major < 3 or (major == 3 and minor < 8):
            result['status'] = 'error'
            result['issues'].append(f'Python {python_version} is too old. Requires Python 3.8+')
        elif major == 3 and minor < 11:
            result['status'] = 'warning'
            result['warnings'].append(f'Python {python_version} works but 3.11+ recommended for best performance')

        # Check virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        result['details']['virtual_environment'] = in_venv

        if not in_venv:
            result['warnings'].append('Not running in a virtual environment. Consider using venv for dependency isolation.')

        # Check pip
        try:
            import pip
            result['details']['pip_version'] = pip.__version__
        except ImportError:
            result['status'] = 'error'
            result['issues'].append('pip is not available. Cannot manage Python packages.')

        return result

    def _check_package_installation(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check package installation and imports"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        # Check core package imports
        core_modules = [
            'click', 'requests', 'rich', 'keyring', 'pydantic', 'yaml', 'toml'
        ]

        missing_modules = []
        for module in core_modules:
            try:
                __import__(module)
                result['details'][f'{module}_available'] = True
            except ImportError:
                missing_modules.append(module)
                result['details'][f'{module}_available'] = False

        if missing_modules:
            result['status'] = 'error'
            result['issues'].append(f'Missing required modules: {", ".join(missing_modules)}')

        # Check godaddy_cli package
        try:
            import godaddy_cli
            result['details']['godaddy_cli_version'] = getattr(godaddy_cli, '__version__', 'unknown')
        except ImportError:
            result['status'] = 'error'
            result['issues'].append('godaddy_cli package is not properly installed')

        return result

    def _check_configuration_files(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check configuration files and structure"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': [], 'fixes_applied': []}

        if not self.config:
            result['status'] = 'warning'
            result['warnings'].append('No configuration manager available')
            return result

        # Check config file existence
        config_file = self.config.config_file
        result['details']['config_file_path'] = str(config_file)
        result['details']['config_file_exists'] = config_file.exists()

        if not config_file.exists():
            if auto_fix:
                try:
                    # Create basic config structure
                    config_file.parent.mkdir(parents=True, exist_ok=True)
                    basic_config = {'profiles': {'default': {}}}
                    with open(config_file, 'w') as f:
                        json.dump(basic_config, f, indent=2)
                    result['fixes_applied'].append(f'Created basic configuration file at {config_file}')
                    result['details']['config_file_exists'] = True
                except Exception as e:
                    result['status'] = 'error'
                    result['issues'].append(f'Cannot create config file: {e}')
            else:
                result['status'] = 'warning'
                result['warnings'].append(f'Configuration file not found: {config_file}')
                return result

        # Validate config file structure
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            result['details']['config_valid_json'] = True

            # Check required structure
            if 'profiles' not in config_data:
                result['status'] = 'error'
                result['issues'].append('Configuration missing "profiles" section')
            elif 'default' not in config_data['profiles']:
                result['status'] = 'warning'
                result['warnings'].append('No default profile configured')

            result['details']['profiles_count'] = len(config_data.get('profiles', {}))

        except json.JSONDecodeError as e:
            result['status'] = 'error'
            result['issues'].append(f'Configuration file is not valid JSON: {e}')
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f'Cannot read configuration file: {e}')

        return result

    def _check_credentials_security(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check credential security and keyring functionality"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        if not self.auth:
            result['status'] = 'warning'
            result['warnings'].append('No authentication manager available')
            return result

        # Check keyring functionality
        try:
            import keyring
            backend = keyring.get_keyring()
            result['details']['keyring_backend'] = str(type(backend).__name__)
            result['details']['keyring_available'] = True
        except ImportError:
            result['status'] = 'error'
            result['issues'].append('Keyring module not available for secure credential storage')
            return result

        # Check if credentials are configured
        try:
            configured = self.auth.is_configured()
            result['details']['credentials_configured'] = configured

            if configured:
                # Test credential retrieval (but don't expose them)
                try:
                    api_key, api_secret = self.auth.get_credentials()
                    result['details']['credentials_retrievable'] = True
                    result['details']['api_key_length'] = len(api_key) if api_key else 0
                    result['details']['api_secret_length'] = len(api_secret) if api_secret else 0

                    # Basic validation
                    if not api_key or len(api_key) < 10:
                        result['status'] = 'warning'
                        result['warnings'].append('API key appears to be too short or missing')

                    if not api_secret or len(api_secret) < 10:
                        result['status'] = 'warning'
                        result['warnings'].append('API secret appears to be too short or missing')

                except Exception as e:
                    result['status'] = 'error'
                    result['issues'].append(f'Cannot retrieve credentials from keyring: {e}')
            else:
                result['status'] = 'warning'
                result['warnings'].append('No API credentials configured. Run "godaddy auth setup"')

        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f'Error checking credentials: {e}')

        return result

    def _check_api_connectivity(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check API connectivity and authentication"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        if not self.auth or not self.auth.is_configured():
            result['status'] = 'warning'
            result['warnings'].append('Cannot test API connectivity - no credentials configured')
            return result

        try:
            # Test API connection
            api_key, api_secret = self.auth.get_credentials()

            with APIClient(api_key, api_secret) as client:
                # Test basic connectivity
                start_time = self._get_timestamp()
                connected = client.test_connection()
                end_time = self._get_timestamp()

                result['details']['api_reachable'] = connected
                result['details']['response_time_ms'] = self._time_diff_ms(start_time, end_time)

                if connected:
                    # Try to get domains to test full authentication
                    try:
                        domains = client.get_domains()
                        result['details']['authentication_valid'] = True
                        result['details']['domains_count'] = len(domains)

                        if len(domains) == 0:
                            result['warnings'].append('API authentication works but no domains found in account')

                    except Exception as e:
                        result['status'] = 'error'
                        result['issues'].append(f'API authentication failed: {e}')
                        result['details']['authentication_valid'] = False
                else:
                    result['status'] = 'error'
                    result['issues'].append('Cannot connect to GoDaddy API')

        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f'API connectivity test failed: {e}')

        return result

    def _check_file_permissions(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check file permissions for config and cache directories"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': [], 'fixes_applied': []}

        if not self.config:
            result['status'] = 'warning'
            result['warnings'].append('No configuration manager available')
            return result

        # Check config directory permissions
        config_dir = self.config.config_file.parent
        result['details']['config_dir_exists'] = config_dir.exists()
        result['details']['config_dir_writable'] = os.access(config_dir, os.W_OK) if config_dir.exists() else False
        result['details']['config_dir_readable'] = os.access(config_dir, os.R_OK) if config_dir.exists() else False

        if config_dir.exists():
            if not os.access(config_dir, os.W_OK):
                result['status'] = 'error'
                result['issues'].append(f'Configuration directory is not writable: {config_dir}')

            if not os.access(config_dir, os.R_OK):
                result['status'] = 'error'
                result['issues'].append(f'Configuration directory is not readable: {config_dir}')
        else:
            if auto_fix:
                try:
                    config_dir.mkdir(parents=True, exist_ok=True)
                    result['fixes_applied'].append(f'Created configuration directory: {config_dir}')
                    result['details']['config_dir_exists'] = True
                    result['details']['config_dir_writable'] = True
                    result['details']['config_dir_readable'] = True
                except Exception as e:
                    result['status'] = 'error'
                    result['issues'].append(f'Cannot create configuration directory: {e}')

        return result

    def _check_dependencies(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check dependency versions and compatibility"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        # Check critical dependencies
        dependencies = {
            'click': {'min_version': '8.0.0'},
            'requests': {'min_version': '2.25.0'},
            'rich': {'min_version': '12.0.0'},
            'keyring': {'min_version': '23.0.0'}
        }

        for dep_name, requirements in dependencies.items():
            try:
                module = __import__(dep_name)
                version = getattr(module, '__version__', 'unknown')
                result['details'][f'{dep_name}_version'] = version

                if version != 'unknown' and 'min_version' in requirements:
                    if self._version_less_than(version, requirements['min_version']):
                        result['status'] = 'warning'
                        result['warnings'].append(
                            f'{dep_name} version {version} is below recommended {requirements["min_version"]}'
                        )

            except ImportError:
                result['status'] = 'error'
                result['issues'].append(f'Required dependency {dep_name} is not installed')

        return result

    def _check_performance(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check performance-related metrics"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        import time
        import psutil

        # Check available memory
        memory = psutil.virtual_memory()
        result['details']['available_memory_mb'] = round(memory.available / 1024 / 1024)
        result['details']['memory_usage_percent'] = memory.percent

        if memory.percent > 90:
            result['status'] = 'warning'
            result['warnings'].append(f'High memory usage: {memory.percent:.1f}%')

        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        result['details']['cpu_usage_percent'] = cpu_percent

        if cpu_percent > 80:
            result['status'] = 'warning'
            result['warnings'].append(f'High CPU usage: {cpu_percent:.1f}%')

        # Simple performance test
        start_time = time.time()
        for _ in range(1000):
            pass  # Simple loop
        end_time = time.time()

        performance_score = 1000 / (end_time - start_time)
        result['details']['performance_score'] = round(performance_score)

        if performance_score < 10000:
            result['warnings'].append('System performance appears slower than expected')

        return result

    def _check_disk_space(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check available disk space"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        import shutil

        if self.config and self.config.config_file:
            config_dir = self.config.config_file.parent

            try:
                total, used, free = shutil.disk_usage(config_dir)
                free_mb = free // (1024 * 1024)
                usage_percent = (used / total) * 100

                result['details']['free_space_mb'] = free_mb
                result['details']['disk_usage_percent'] = round(usage_percent, 1)

                if free_mb < 100:  # Less than 100MB
                    result['status'] = 'error'
                    result['issues'].append(f'Very low disk space: {free_mb}MB available')
                elif free_mb < 500:  # Less than 500MB
                    result['status'] = 'warning'
                    result['warnings'].append(f'Low disk space: {free_mb}MB available')

            except Exception as e:
                result['status'] = 'warning'
                result['warnings'].append(f'Cannot check disk space: {e}')

        return result

    def _check_network_connectivity(self, verbose: bool = False, auto_fix: bool = False) -> Dict[str, Any]:
        """Check network connectivity to GoDaddy API"""
        result = {'status': 'healthy', 'details': {}, 'issues': [], 'warnings': []}

        import socket
        import urllib.request

        # Test DNS resolution
        try:
            socket.gethostbyname('api.godaddy.com')
            result['details']['dns_resolution'] = True
        except socket.gaierror:
            result['status'] = 'error'
            result['issues'].append('Cannot resolve api.godaddy.com - DNS issues')
            result['details']['dns_resolution'] = False

        # Test HTTPS connectivity
        try:
            with urllib.request.urlopen('https://api.godaddy.com', timeout=10) as response:
                result['details']['https_connectivity'] = response.status == 200
        except Exception as e:
            result['status'] = 'warning'
            result['warnings'].append(f'HTTPS connectivity issue: {e}')
            result['details']['https_connectivity'] = False

        return result

    def display_results(self, results: Dict[str, Any], verbose: bool = False):
        """Display diagnostic results in a user-friendly format"""
        # Overall health status
        health_color = {
            'healthy': 'green',
            'warning': 'yellow',
            'critical': 'red'
        }

        health_icon = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '❌'
        }

        overall_health = results['overall_health']

        console.print(Panel(
            f"{health_icon[overall_health]} [bold {health_color[overall_health]}]System Health: {overall_health.upper()}[/bold {health_color[overall_health]}]",
            border_style=health_color[overall_health]
        ))

        # Summary table
        table = Table(title="Diagnostic Summary", box=box.ROUNDED)
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")

        for check_name, check_result in results['checks'].items():
            status = check_result['status']
            status_icon = '✅' if status == 'healthy' else '⚠️' if status == 'warning' else '❌'
            status_text = f"{status_icon} {status.title()}"

            details = check_result.get('message', '')
            if verbose and 'details' in check_result:
                detail_items = [f"{k}: {v}" for k, v in check_result['details'].items()]
                details = '; '.join(detail_items[:3])  # Limit details

            table.add_row(
                check_name.replace('_', ' ').title(),
                status_text,
                details
            )

        console.print(table)

        # Issues and warnings
        if results['issues']:
            console.print(Panel(
                '\n'.join([f"• {issue}" for issue in results['issues']]),
                title="[bold red]Critical Issues[/bold red]",
                border_style="red"
            ))

        if results['warnings']:
            console.print(Panel(
                '\n'.join([f"• {warning}" for warning in results['warnings']]),
                title="[bold yellow]Warnings[/bold yellow]",
                border_style="yellow"
            ))

        # Fixes applied
        if results['fixes_applied']:
            console.print(Panel(
                '\n'.join([f"✅ {fix}" for fix in results['fixes_applied']]),
                title="[bold green]Fixes Applied[/bold green]",
                border_style="green"
            ))

        # Recommendations
        self._show_recommendations(results)

    def _show_recommendations(self, results: Dict[str, Any]):
        """Show recommendations based on diagnostic results"""
        recommendations = []

        if results['overall_health'] == 'critical':
            recommendations.append("🚨 Critical issues detected. Please address them before using the CLI.")

        if results['overall_health'] == 'warning':
            recommendations.append("⚠️ Some warnings detected. Consider addressing them for optimal performance.")

        # Specific recommendations based on check results
        checks = results['checks']

        if 'credentials_security' in checks and checks['credentials_security']['status'] != 'healthy':
            recommendations.append("🔐 Run 'godaddy auth setup' to configure your API credentials")

        if 'api_connectivity' in checks and checks['api_connectivity']['status'] != 'healthy':
            recommendations.append("🌐 Check your internet connection and API credentials")

        if 'configuration_files' in checks and checks['configuration_files']['status'] != 'healthy':
            recommendations.append("⚙️ Run 'godaddy doctor --fix' to repair configuration files")

        if recommendations:
            console.print(Panel(
                '\n'.join(recommendations),
                title="[bold blue]Recommendations[/bold blue]",
                border_style="blue"
            ))

    def export_report(self, results: Dict[str, Any], filepath: str):
        """Export diagnostic report to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        except Exception as e:
            console.print(f"[red]Failed to export report: {e}[/red]")

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _get_system_info(self) -> Dict[str, str]:
        """Get basic system information"""
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
            'machine': platform.machine(),
            'processor': platform.processor()
        }

    def _time_diff_ms(self, start: str, end: str) -> float:
        """Calculate time difference in milliseconds"""
        from datetime import datetime
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        return (end_dt - start_dt).total_seconds() * 1000

    def _version_less_than(self, current: str, minimum: str) -> bool:
        """Compare version strings"""
        def parse_version(v):
            return tuple(map(int, v.split('.')))

        try:
            return parse_version(current) < parse_version(minimum)
        except:
            return False  # If we can't parse, assume it's ok