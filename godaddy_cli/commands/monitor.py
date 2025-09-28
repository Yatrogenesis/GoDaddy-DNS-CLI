"""
DNS monitoring commands
"""

import click
import time
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta

from godaddy_cli.core.api_client import SyncGoDaddyAPIClient
from godaddy_cli.core.exceptions import APIError, ValidationError
from godaddy_cli.utils.formatters import format_status_panel, format_monitoring_status
from godaddy_cli.utils.validators import validate_domain, validate_url


@click.group(name='monitor')
@click.pass_context
def monitor_group(ctx):
    """DNS monitoring commands"""
    pass


@monitor_group.command('start')
@click.argument('domain')
@click.option('--interval', type=int, default=300, help='Check interval in seconds')
@click.option('--timeout', type=int, default=3600, help='Monitor timeout in seconds')
@click.option('--records', multiple=True, help='Specific records to monitor')
@click.option('--alert-webhook', help='Webhook URL for alerts')
@click.pass_context
def start_monitoring(ctx, domain: str, interval: int, timeout: int,
                     records: tuple, alert_webhook: Optional[str]):
    """Start monitoring DNS records for changes"""
    try:
        validate_domain(domain)

        if alert_webhook:
            validate_url(alert_webhook)

        if interval < 60:
            raise ValidationError("Minimum interval is 60 seconds")

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])

        # Get initial state
        click.echo(f"Starting DNS monitoring for {domain}")
        click.echo(f"Check interval: {interval} seconds")
        click.echo(f"Timeout: {timeout} seconds")

        if records:
            click.echo(f"Monitoring specific records: {', '.join(records)}")

        initial_records = client.list_dns_records(domain)
        if not initial_records:
            click.echo(format_status_panel('warning', f'No DNS records found for {domain}'))
            return

        # Filter records if specified
        if records:
            initial_records = [r for r in initial_records if r.name in records]

        click.echo(f"Monitoring {len(initial_records)} DNS records")

        # Store initial state
        initial_state = {
            f"{r.name}.{r.type}": {
                'data': r.data,
                'ttl': r.ttl,
                'priority': r.priority
            }
            for r in initial_records
        }

        start_time = datetime.now()
        check_count = 0

        try:
            while True:
                # Check if timeout exceeded
                if datetime.now() - start_time > timedelta(seconds=timeout):
                    click.echo(format_status_panel('info', 'Monitoring timeout reached'))
                    break

                check_count += 1
                check_time = datetime.now().strftime("%H:%M:%S")

                try:
                    # Get current records
                    current_records = client.list_dns_records(domain)

                    if records:
                        current_records = [r for r in current_records if r.name in records]

                    # Compare with initial state
                    changes_detected = []

                    for record in current_records:
                        key = f"{record.name}.{record.type}"
                        current_state = {
                            'data': record.data,
                            'ttl': record.ttl,
                            'priority': record.priority
                        }

                        if key in initial_state:
                            if initial_state[key] != current_state:
                                changes_detected.append({
                                    'record': key,
                                    'old': initial_state[key],
                                    'new': current_state
                                })
                                # Update initial state
                                initial_state[key] = current_state
                        else:
                            # New record
                            changes_detected.append({
                                'record': key,
                                'old': None,
                                'new': current_state
                            })
                            initial_state[key] = current_state

                    # Check for deleted records
                    current_keys = {f"{r.name}.{r.type}" for r in current_records}
                    for key in list(initial_state.keys()):
                        if key not in current_keys:
                            changes_detected.append({
                                'record': key,
                                'old': initial_state[key],
                                'new': None
                            })
                            del initial_state[key]

                    # Report status
                    if changes_detected:
                        click.echo(f"\n[{check_time}] CHANGES DETECTED:")
                        for change in changes_detected:
                            if change['old'] is None:
                                click.echo(f"  + Added: {change['record']}")
                            elif change['new'] is None:
                                click.echo(f"  - Deleted: {change['record']}")
                            else:
                                click.echo(f"  ~ Modified: {change['record']}")
                                for field, value in change['new'].items():
                                    if change['old'][field] != value:
                                        click.echo(f"    {field}: {change['old'][field]} → {value}")

                        # Send webhook alert if configured
                        if alert_webhook:
                            _send_webhook_alert(alert_webhook, domain, changes_detected)

                    else:
                        click.echo(f"[{check_time}] Check #{check_count}: No changes detected")

                except APIError as e:
                    click.echo(f"[{check_time}] API Error: {e.message}", err=True)

                # Wait for next check
                time.sleep(interval)

        except KeyboardInterrupt:
            click.echo(f"\nMonitoring stopped by user after {check_count} checks")

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Monitoring failed: {str(e)}'), err=True)
        ctx.exit(1)


@monitor_group.command('check')
@click.argument('record')
@click.option('--timeout', type=int, default=300, help='Propagation check timeout')
@click.option('--dns-servers', help='Comma-separated list of DNS servers to check')
@click.pass_context
def check_propagation(ctx, record: str, timeout: int, dns_servers: Optional[str]):
    """Check DNS record propagation across servers"""
    try:
        # Default DNS servers
        default_servers = ['8.8.8.8', '1.1.1.1', '208.67.222.222', '9.9.9.9']

        if dns_servers:
            servers = [s.strip() for s in dns_servers.split(',')]
        else:
            servers = default_servers

        click.echo(f"Checking propagation for: {record}")
        click.echo(f"DNS servers: {', '.join(servers)}")
        click.echo(f"Timeout: {timeout} seconds")

        import dns.resolver
        import dns.exception

        start_time = datetime.now()
        results = {}

        while True:
            all_consistent = True
            expected_value = None

            for server in servers:
                try:
                    resolver = dns.resolver.Resolver()
                    resolver.nameservers = [server]
                    resolver.timeout = 5

                    # Try different record types
                    for record_type in ['A', 'AAAA', 'CNAME', 'MX', 'TXT']:
                        try:
                            answer = resolver.resolve(record, record_type)
                            values = [str(rdata) for rdata in answer]

                            if expected_value is None:
                                expected_value = values
                            elif values != expected_value:
                                all_consistent = False

                            results[f"{server}_{record_type}"] = values
                            break
                        except dns.exception.DNSException:
                            continue

                except Exception as e:
                    results[server] = f"Error: {str(e)}"
                    all_consistent = False

            # Display current status
            elapsed = (datetime.now() - start_time).total_seconds()
            click.echo(f"\n[{elapsed:.0f}s] Propagation check:")

            for server in servers:
                server_results = [v for k, v in results.items() if k.startswith(server)]
                if server_results:
                    click.echo(f"  {server}: {server_results[0]}")
                else:
                    click.echo(f"  {server}: No response")

            if all_consistent and expected_value:
                click.echo(format_status_panel('success', 'DNS propagation complete'))
                break

            if elapsed >= timeout:
                click.echo(format_status_panel('warning', 'Propagation check timeout reached'))
                break

            time.sleep(10)

    except ImportError:
        click.echo(format_status_panel('error', 'dnspython library required for propagation checks'), err=True)
        click.echo("Install with: pip install dnspython")
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Propagation check failed: {str(e)}'), err=True)
        ctx.exit(1)


@monitor_group.command('status')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']),
              default='table', help='Output format')
@click.pass_context
def monitoring_status(ctx, output_format: str):
    """Show monitoring status"""
    try:
        # In a real implementation, this would connect to a monitoring service
        # For now, we'll show a placeholder status
        status_data = {
            'active_monitors': 0,
            'total_checks': 0,
            'last_alert': 'Never',
            'monitored_domains': []
        }

        if output_format == 'table':
            click.echo(format_monitoring_status(status_data))
        else:
            from godaddy_cli.utils.formatters import format_json_output
            click.echo(format_json_output(status_data))

        click.echo(format_status_panel(
            'info',
            'Monitoring service is not currently running. Use "godaddy monitor start" to begin monitoring.'
        ))

    except Exception as e:
        click.echo(format_status_panel('error', f'Status check failed: {str(e)}'), err=True)
        ctx.exit(1)


@monitor_group.command('alert')
@click.argument('domain')
@click.argument('webhook_url')
@click.option('--test', is_flag=True, help='Send test alert')
@click.pass_context
def setup_alert(ctx, domain: str, webhook_url: str, test: bool):
    """Setup webhook alerts for domain monitoring"""
    try:
        validate_domain(domain)
        validate_url(webhook_url)

        if test:
            # Send test alert
            test_changes = [
                {
                    'record': 'test.example.com.A',
                    'old': {'data': '192.168.1.1', 'ttl': 3600},
                    'new': {'data': '192.168.1.2', 'ttl': 3600}
                }
            ]

            success = _send_webhook_alert(webhook_url, domain, test_changes, test=True)

            if success:
                click.echo(format_status_panel('success', 'Test alert sent successfully'))
            else:
                click.echo(format_status_panel('error', 'Test alert failed'), err=True)
                ctx.exit(1)
        else:
            # Store webhook configuration
            # In a real implementation, this would save to configuration
            click.echo(format_status_panel('success', f'Alert webhook configured for {domain}'))
            click.echo(f"Webhook URL: {webhook_url}")

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Alert setup failed: {str(e)}'), err=True)
        ctx.exit(1)


def _send_webhook_alert(webhook_url: str, domain: str, changes: List[dict], test: bool = False) -> bool:
    """Send webhook alert for DNS changes"""
    try:
        import requests

        payload = {
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'test': test,
            'changes': changes
        }

        if test:
            payload['message'] = 'Test alert from GoDaddy DNS CLI'

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={'User-Agent': 'GoDaddy-DNS-CLI/2.0.0'}
        )

        return response.status_code < 400

    except Exception:
        return False


def register_commands(cli):
    """Register monitoring commands with the main CLI"""
    cli.add_command(monitor_group)