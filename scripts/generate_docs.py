#!/usr/bin/env python3
"""
Generate comprehensive API documentation from docstrings
"""

import ast
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from godaddy_cli.core.simple_api_client import APIClient as SimpleAPIClient, DNSRecord, Domain
    from godaddy_cli.core.auth import AuthManager
    from godaddy_cli.core.config import ConfigManager
    # Import only what exists
    SimpleAPIClient = None
    try:
        from godaddy_cli.core.simple_api_client import APIClient as SimpleAPIClient
    except ImportError:
        pass
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    SimpleAPIClient = None


class DocGenerator:
    """Generate comprehensive documentation from Python code"""

    def __init__(self):
        self.docs = {
            'api_reference': {},
            'cli_commands': {},
            'utils': {},
            'examples': {},
            'generated_at': datetime.now().isoformat()
        }

    def extract_function_info(self, func) -> Dict[str, Any]:
        """Extract detailed information from a function"""
        info = {
            'name': func.__name__,
            'docstring': inspect.getdoc(func) or '',
            'signature': str(inspect.signature(func)),
            'parameters': [],
            'returns': '',
            'examples': []
        }

        # Parse docstring for parameters and return type
        docstring = info['docstring']
        if docstring:
            lines = docstring.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()
                if line.startswith('Args:') or line.startswith('Parameters:'):
                    current_section = 'args'
                elif line.startswith('Returns:'):
                    current_section = 'returns'
                elif line.startswith('Example') or line.startswith('Usage'):
                    current_section = 'examples'
                elif current_section == 'args' and ':' in line:
                    param_info = line.split(':', 1)
                    if len(param_info) == 2:
                        info['parameters'].append({
                            'name': param_info[0].strip(),
                            'description': param_info[1].strip()
                        })
                elif current_section == 'returns' and line:
                    info['returns'] = line
                elif current_section == 'examples' and line:
                    info['examples'].append(line)

        return info

    def extract_class_info(self, cls) -> Dict[str, Any]:
        """Extract detailed information from a class"""
        info = {
            'name': cls.__name__,
            'docstring': inspect.getdoc(cls) or '',
            'methods': {},
            'attributes': [],
            'inheritance': [base.__name__ for base in cls.__bases__ if base.__name__ != 'object']
        }

        # Extract public methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):
                info['methods'][name] = self.extract_function_info(method)

        return info

    def document_api_client(self):
        """Document API client classes"""
        try:
            # Document SimpleAPIClient if available
            if SimpleAPIClient:
                simple_client_info = self.extract_class_info(SimpleAPIClient)
                self.docs['api_reference']['SimpleAPIClient'] = simple_client_info

            # Document data classes
            self.docs['api_reference']['DNSRecord'] = {
                'name': 'DNSRecord',
                'type': 'dataclass',
                'docstring': 'DNS record data structure',
                'fields': [
                    {'name': 'name', 'type': 'str', 'description': 'Record name'},
                    {'name': 'type', 'type': 'str', 'description': 'Record type (A, AAAA, CNAME, etc.)'},
                    {'name': 'data', 'type': 'str', 'description': 'Record data/value'},
                    {'name': 'ttl', 'type': 'int', 'description': 'Time to live in seconds', 'default': 3600},
                    {'name': 'priority', 'type': 'Optional[int]', 'description': 'Priority for MX/SRV records'},
                    {'name': 'port', 'type': 'Optional[int]', 'description': 'Port for SRV records'},
                    {'name': 'weight', 'type': 'Optional[int]', 'description': 'Weight for SRV records'},
                ]
            }

            self.docs['api_reference']['Domain'] = {
                'name': 'Domain',
                'type': 'dataclass',
                'docstring': 'Domain information structure',
                'fields': [
                    {'name': 'domain', 'type': 'str', 'description': 'Domain name'},
                    {'name': 'status', 'type': 'str', 'description': 'Domain status'},
                    {'name': 'expires', 'type': 'str', 'description': 'Expiration date'},
                    {'name': 'privacy', 'type': 'bool', 'description': 'Privacy protection enabled'},
                    {'name': 'locked', 'type': 'bool', 'description': 'Domain locked status'},
                ]
            }

        except Exception as e:
            print(f"Error documenting API client: {e}")

    def document_cli_commands(self):
        """Document CLI command groups and their subcommands"""
        commands = {
            'dns': {
                'module': 'godaddy_cli.commands.dns',
                'description': 'DNS record management commands',
                'subcommands': {
                    'list': {
                        'description': 'List DNS records for a domain',
                        'usage': 'godaddy dns list DOMAIN [OPTIONS]',
                        'options': [
                            {'name': '--type', 'description': 'Filter by record type'},
                            {'name': '--name', 'description': 'Filter by record name'},
                            {'name': '--format', 'description': 'Output format (table, json, yaml, csv)'},
                            {'name': '--export', 'description': 'Export to file'},
                        ],
                        'examples': [
                            'godaddy dns list example.com',
                            'godaddy dns list example.com --type A',
                            'godaddy dns list example.com --format json',
                            'godaddy dns list example.com --export records.csv'
                        ]
                    },
                    'add': {
                        'description': 'Add a DNS record',
                        'usage': 'godaddy dns add DOMAIN --name NAME --type TYPE --data DATA [OPTIONS]',
                        'options': [
                            {'name': '--name', 'description': 'Record name', 'required': True},
                            {'name': '--type', 'description': 'Record type', 'required': True},
                            {'name': '--data', 'description': 'Record data', 'required': True},
                            {'name': '--ttl', 'description': 'Time to live (default: 3600)'},
                            {'name': '--priority', 'description': 'Priority for MX records'},
                        ],
                        'examples': [
                            'godaddy dns add example.com --name www --type A --data 192.168.1.1',
                            'godaddy dns add example.com --name mail --type MX --data mail.example.com --priority 10',
                            'godaddy dns add example.com --name @ --type TXT --data "v=spf1 mx ~all"'
                        ]
                    },
                    'update': {
                        'description': 'Update an existing DNS record',
                        'usage': 'godaddy dns update DOMAIN --name NAME --type TYPE --data DATA [OPTIONS]',
                        'options': [
                            {'name': '--name', 'description': 'Record name', 'required': True},
                            {'name': '--type', 'description': 'Record type', 'required': True},
                            {'name': '--data', 'description': 'New record data', 'required': True},
                            {'name': '--ttl', 'description': 'Time to live'},
                        ],
                        'examples': [
                            'godaddy dns update example.com --name www --type A --data 192.168.1.2',
                            'godaddy dns update example.com --name @ --type A --data 192.168.1.1 --ttl 7200'
                        ]
                    },
                    'delete': {
                        'description': 'Delete a DNS record',
                        'usage': 'godaddy dns delete DOMAIN --name NAME --type TYPE [OPTIONS]',
                        'options': [
                            {'name': '--name', 'description': 'Record name', 'required': True},
                            {'name': '--type', 'description': 'Record type', 'required': True},
                            {'name': '--force', 'description': 'Skip confirmation'},
                        ],
                        'examples': [
                            'godaddy dns delete example.com --name old --type A',
                            'godaddy dns delete example.com --name test --type CNAME --force'
                        ]
                    }
                }
            },
            'domains': {
                'module': 'godaddy_cli.commands.domain',
                'description': 'Domain management commands',
                'subcommands': {
                    'list': {
                        'description': 'List all domains in your account',
                        'usage': 'godaddy domains list [OPTIONS]',
                        'options': [
                            {'name': '--format', 'description': 'Output format (table, json)'},
                            {'name': '--status', 'description': 'Filter by status'},
                        ],
                        'examples': [
                            'godaddy domains list',
                            'godaddy domains list --format json',
                            'godaddy domains list --status ACTIVE'
                        ]
                    },
                    'info': {
                        'description': 'Get detailed information about a domain',
                        'usage': 'godaddy domains info DOMAIN',
                        'examples': [
                            'godaddy domains info example.com'
                        ]
                    }
                }
            },
            'auth': {
                'module': 'godaddy_cli.commands.auth',
                'description': 'Authentication and credential management',
                'subcommands': {
                    'setup': {
                        'description': 'Configure API credentials',
                        'usage': 'godaddy auth setup [OPTIONS]',
                        'options': [
                            {'name': '--api-key', 'description': 'GoDaddy API key'},
                            {'name': '--api-secret', 'description': 'GoDaddy API secret'},
                            {'name': '--profile', 'description': 'Configuration profile name'},
                        ],
                        'examples': [
                            'godaddy auth setup',
                            'godaddy auth setup --profile production'
                        ]
                    },
                    'test': {
                        'description': 'Test API connection',
                        'usage': 'godaddy auth test',
                        'examples': ['godaddy auth test']
                    }
                }
            },
            'bulk': {
                'module': 'godaddy_cli.commands.bulk',
                'description': 'Bulk operations for multiple DNS records',
                'subcommands': {
                    'import': {
                        'description': 'Import DNS records from CSV file',
                        'usage': 'godaddy bulk import DOMAIN --file FILE [OPTIONS]',
                        'options': [
                            {'name': '--file', 'description': 'CSV file path', 'required': True},
                            {'name': '--dry-run', 'description': 'Show what would be imported'},
                            {'name': '--replace', 'description': 'Replace existing records'},
                        ],
                        'examples': [
                            'godaddy bulk import example.com --file records.csv',
                            'godaddy bulk import example.com --file records.csv --dry-run'
                        ]
                    },
                    'export': {
                        'description': 'Export DNS records to file',
                        'usage': 'godaddy bulk export DOMAIN [OPTIONS]',
                        'options': [
                            {'name': '--format', 'description': 'Export format (csv, json, yaml)'},
                            {'name': '--output', 'description': 'Output file path'},
                        ],
                        'examples': [
                            'godaddy bulk export example.com --format csv',
                            'godaddy bulk export example.com --output backup.json'
                        ]
                    }
                }
            }
        }

        self.docs['cli_commands'] = commands

    def document_utilities(self):
        """Document utility modules"""
        self.docs['utils'] = {
            'validators': {
                'description': 'Input validation utilities',
                'functions': {
                    'validate_domain': {
                        'description': 'Validate domain name format',
                        'parameters': [{'name': 'domain', 'type': 'str', 'description': 'Domain to validate'}],
                        'returns': 'bool - True if valid',
                        'examples': ['validate_domain("example.com")  # True']
                    },
                    'validate_ip': {
                        'description': 'Validate IP address format',
                        'parameters': [{'name': 'ip', 'type': 'str', 'description': 'IP address to validate'}],
                        'returns': 'bool - True if valid',
                        'examples': ['validate_ip("192.168.1.1")  # True']
                    },
                    'validate_ttl': {
                        'description': 'Validate TTL value',
                        'parameters': [{'name': 'ttl', 'type': 'int', 'description': 'TTL value to validate'}],
                        'returns': 'bool - True if valid (300-604800)',
                        'examples': ['validate_ttl(3600)  # True']
                    }
                }
            },
            'formatters': {
                'description': 'Output formatting utilities',
                'functions': {
                    'format_dns_table': {
                        'description': 'Format DNS records as a table',
                        'parameters': [
                            {'name': 'records', 'type': 'List[DNSRecord]', 'description': 'DNS records to format'},
                            {'name': 'title', 'type': 'str', 'description': 'Table title'}
                        ],
                        'returns': 'str - Formatted table string'
                    },
                    'format_json_output': {
                        'description': 'Format data as JSON',
                        'parameters': [
                            {'name': 'data', 'type': 'Any', 'description': 'Data to format'},
                            {'name': 'pretty', 'type': 'bool', 'description': 'Pretty print format'}
                        ],
                        'returns': 'str - JSON string'
                    }
                }
            },
            'error_handlers': {
                'description': 'Enhanced error handling utilities',
                'classes': {
                    'UserFriendlyErrorHandler': {
                        'description': 'Enhanced error handler with specific user guidance',
                        'methods': {
                            'handle_api_response_error': {
                                'description': 'Handle API response errors with specific guidance',
                                'static': True
                            },
                            'display_error_with_suggestions': {
                                'description': 'Display error with rich formatting and suggestions',
                                'static': True
                            }
                        }
                    }
                }
            }
        }

    def generate_examples(self):
        """Generate practical usage examples"""
        self.docs['examples'] = {
            'getting_started': {
                'title': 'Getting Started',
                'steps': [
                    {
                        'step': 1,
                        'title': 'Install the CLI',
                        'commands': [
                            'pip install godaddy-dns-cli',
                            '# or install from source',
                            'git clone https://github.com/Yatrogenesis/GoDaddy-DNS-CLI.git',
                            'cd GoDaddy-DNS-CLI',
                            'pip install -e .'
                        ]
                    },
                    {
                        'step': 2,
                        'title': 'Configure API credentials',
                        'commands': [
                            'godaddy auth setup',
                            '# Follow the prompts to enter your API key and secret'
                        ],
                        'notes': [
                            'Get your API credentials from https://developer.godaddy.com/keys',
                            'Choose "Production" for live domains or "OTE" for testing'
                        ]
                    },
                    {
                        'step': 3,
                        'title': 'Test connection',
                        'commands': ['godaddy auth test']
                    },
                    {
                        'step': 4,
                        'title': 'List your domains',
                        'commands': ['godaddy domains list']
                    },
                    {
                        'step': 5,
                        'title': 'Manage DNS records',
                        'commands': [
                            'godaddy dns list example.com',
                            'godaddy dns add example.com --name www --type A --data 192.168.1.1'
                        ]
                    }
                ]
            },
            'common_tasks': {
                'title': 'Common DNS Management Tasks',
                'scenarios': [
                    {
                        'title': 'Setting up a web server',
                        'description': 'Configure DNS for a typical web application',
                        'commands': [
                            '# Add main domain A record',
                            'godaddy dns add example.com --name @ --type A --data 192.168.1.1',
                            '',
                            '# Add www subdomain',
                            'godaddy dns add example.com --name www --type CNAME --data example.com',
                            '',
                            '# Add API subdomain',
                            'godaddy dns add example.com --name api --type A --data 192.168.1.2'
                        ]
                    },
                    {
                        'title': 'Email server setup',
                        'description': 'Configure DNS records for email hosting',
                        'commands': [
                            '# Add MX record',
                            'godaddy dns add example.com --name @ --type MX --data mail.example.com --priority 10',
                            '',
                            '# Add mail server A record',
                            'godaddy dns add example.com --name mail --type A --data 192.168.1.10',
                            '',
                            '# Add SPF record',
                            'godaddy dns add example.com --name @ --type TXT --data "v=spf1 mx ~all"',
                            '',
                            '# Add DMARC record',
                            'godaddy dns add example.com --name _dmarc --type TXT --data "v=DMARC1; p=none; rua=mailto:dmarc@example.com"'
                        ]
                    },
                    {
                        'title': 'Bulk operations',
                        'description': 'Import/export multiple DNS records',
                        'commands': [
                            '# Export existing records',
                            'godaddy bulk export example.com --format csv --output backup.csv',
                            '',
                            '# Import records from CSV',
                            'godaddy bulk import example.com --file new-records.csv',
                            '',
                            '# Dry run to preview changes',
                            'godaddy bulk import example.com --file new-records.csv --dry-run'
                        ]
                    }
                ]
            },
            'advanced_usage': {
                'title': 'Advanced Features',
                'scenarios': [
                    {
                        'title': 'Using templates',
                        'description': 'Apply pre-configured DNS setups',
                        'commands': [
                            '# List available templates',
                            'godaddy template list',
                            '',
                            '# Apply web application template',
                            'godaddy template apply example.com web-app --var app_ip=192.168.1.1'
                        ]
                    },
                    {
                        'title': 'Monitoring and validation',
                        'description': 'Monitor DNS health and validate configuration',
                        'commands': [
                            '# Validate DNS configuration',
                            'godaddy dns validate example.com',
                            '',
                            '# Start monitoring',
                            'godaddy monitor start example.com --interval 300'
                        ]
                    },
                    {
                        'title': 'Multiple profiles',
                        'description': 'Manage multiple accounts or environments',
                        'commands': [
                            '# Setup production profile',
                            'godaddy auth setup --profile production',
                            '',
                            '# Setup development profile',
                            'godaddy auth setup --profile development',
                            '',
                            '# Use specific profile',
                            'godaddy --profile production dns list example.com'
                        ]
                    }
                ]
            }
        }

    def generate_markdown_docs(self) -> str:
        """Generate comprehensive markdown documentation"""
        md = []

        # Header
        md.append("# GoDaddy DNS CLI - Complete API Reference")
        md.append("")
        md.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        md.append("")

        # Table of Contents
        md.append("## Table of Contents")
        md.append("")
        md.append("1. [API Reference](#api-reference)")
        md.append("2. [CLI Commands](#cli-commands)")
        md.append("3. [Utilities](#utilities)")
        md.append("4. [Examples](#examples)")
        md.append("")

        # API Reference
        md.append("## API Reference")
        md.append("")

        for class_name, class_info in self.docs['api_reference'].items():
            md.append(f"### {class_name}")
            md.append("")
            md.append(class_info.get('docstring', ''))
            md.append("")

            if class_info.get('type') == 'dataclass':
                md.append("#### Fields")
                md.append("")
                md.append("| Field | Type | Description | Default |")
                md.append("|-------|------|-------------|---------|")
                for field in class_info.get('fields', []):
                    default = field.get('default', '')
                    if default:
                        default = f"`{default}`"
                    md.append(f"| `{field['name']}` | `{field['type']}` | {field['description']} | {default} |")
                md.append("")

            elif 'methods' in class_info:
                md.append("#### Methods")
                md.append("")
                for method_name, method_info in class_info['methods'].items():
                    md.append(f"##### `{method_name}{method_info['signature']}`")
                    md.append("")
                    md.append(method_info['docstring'])
                    md.append("")

                    if method_info['parameters']:
                        md.append("**Parameters:**")
                        md.append("")
                        for param in method_info['parameters']:
                            md.append(f"- `{param['name']}`: {param['description']}")
                        md.append("")

                    if method_info['returns']:
                        md.append(f"**Returns:** {method_info['returns']}")
                        md.append("")

                    if method_info['examples']:
                        md.append("**Examples:**")
                        md.append("")
                        md.append("```python")
                        for example in method_info['examples']:
                            md.append(example)
                        md.append("```")
                        md.append("")

        # CLI Commands
        md.append("## CLI Commands")
        md.append("")

        for cmd_name, cmd_info in self.docs['cli_commands'].items():
            md.append(f"### `godaddy {cmd_name}`")
            md.append("")
            md.append(cmd_info['description'])
            md.append("")

            for subcmd_name, subcmd_info in cmd_info['subcommands'].items():
                md.append(f"#### `godaddy {cmd_name} {subcmd_name}`")
                md.append("")
                md.append(subcmd_info['description'])
                md.append("")
                md.append(f"**Usage:** `{subcmd_info['usage']}`")
                md.append("")

                if subcmd_info.get('options'):
                    md.append("**Options:**")
                    md.append("")
                    for option in subcmd_info['options']:
                        required = " *(required)*" if option.get('required') else ""
                        md.append(f"- `{option['name']}`: {option['description']}{required}")
                    md.append("")

                if subcmd_info.get('examples'):
                    md.append("**Examples:**")
                    md.append("")
                    md.append("```bash")
                    for example in subcmd_info['examples']:
                        md.append(example)
                    md.append("```")
                    md.append("")

        # Utilities
        md.append("## Utilities")
        md.append("")

        for util_name, util_info in self.docs['utils'].items():
            md.append(f"### {util_name}")
            md.append("")
            md.append(util_info['description'])
            md.append("")

            if 'functions' in util_info:
                for func_name, func_info in util_info['functions'].items():
                    md.append(f"#### `{func_name}()`")
                    md.append("")
                    md.append(func_info['description'])
                    md.append("")

                    if func_info.get('parameters'):
                        md.append("**Parameters:**")
                        md.append("")
                        for param in func_info['parameters']:
                            md.append(f"- `{param['name']}` ({param['type']}): {param['description']}")
                        md.append("")

                    if func_info.get('returns'):
                        md.append(f"**Returns:** {func_info['returns']}")
                        md.append("")

                    if func_info.get('examples'):
                        md.append("**Examples:**")
                        md.append("")
                        md.append("```python")
                        for example in func_info['examples']:
                            md.append(example)
                        md.append("```")
                        md.append("")

        # Examples
        md.append("## Examples")
        md.append("")

        for example_category, category_info in self.docs['examples'].items():
            md.append(f"### {category_info['title']}")
            md.append("")

            if 'steps' in category_info:
                for step in category_info['steps']:
                    md.append(f"#### Step {step['step']}: {step['title']}")
                    md.append("")

                    if step.get('commands'):
                        md.append("```bash")
                        for cmd in step['commands']:
                            md.append(cmd)
                        md.append("```")
                        md.append("")

                    if step.get('notes'):
                        md.append("**Notes:**")
                        md.append("")
                        for note in step['notes']:
                            md.append(f"- {note}")
                        md.append("")

            elif 'scenarios' in category_info:
                for scenario in category_info['scenarios']:
                    md.append(f"#### {scenario['title']}")
                    md.append("")
                    md.append(scenario['description'])
                    md.append("")
                    md.append("```bash")
                    for cmd in scenario['commands']:
                        md.append(cmd)
                    md.append("```")
                    md.append("")

        return '\n'.join(md)

    def generate_json_docs(self) -> str:
        """Generate JSON documentation for API consumption"""
        return json.dumps(self.docs, indent=2, default=str)

    def generate(self):
        """Generate all documentation"""
        print("Generating API documentation...")

        self.document_api_client()
        print("OK API client documented")

        self.document_cli_commands()
        print("OK CLI commands documented")

        self.document_utilities()
        print("OK Utilities documented")

        self.generate_examples()
        print("OK Examples generated")

        # Create docs directory
        docs_dir = project_root / 'docs' / 'api'
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Generate markdown documentation
        markdown_content = self.generate_markdown_docs()
        markdown_file = docs_dir / 'complete_reference.md'
        markdown_file.write_text(markdown_content, encoding='utf-8')
        print(f"OK Markdown documentation saved to {markdown_file}")

        # Generate JSON documentation
        json_content = self.generate_json_docs()
        json_file = docs_dir / 'api_reference.json'
        json_file.write_text(json_content, encoding='utf-8')
        print(f"OK JSON documentation saved to {json_file}")

        # Generate quick reference
        self.generate_quick_reference(docs_dir)
        print("OK Quick reference generated")

        print(f"\nDocumentation generated successfully!")
        print(f"View at: {markdown_file}")

    def generate_quick_reference(self, docs_dir: Path):
        """Generate a quick reference guide"""
        quick_ref = []

        quick_ref.append("# GoDaddy DNS CLI - Quick Reference")
        quick_ref.append("")
        quick_ref.append("## Essential Commands")
        quick_ref.append("")
        quick_ref.append("```bash")
        quick_ref.append("# Setup")
        quick_ref.append("godaddy auth setup                    # Configure API credentials")
        quick_ref.append("godaddy auth test                     # Test connection")
        quick_ref.append("")
        quick_ref.append("# Domains")
        quick_ref.append("godaddy domains list                  # List all domains")
        quick_ref.append("godaddy domains info example.com      # Domain details")
        quick_ref.append("")
        quick_ref.append("# DNS Records")
        quick_ref.append("godaddy dns list example.com          # List DNS records")
        quick_ref.append("godaddy dns add example.com --name www --type A --data 1.2.3.4")
        quick_ref.append("godaddy dns update example.com --name www --type A --data 1.2.3.5")
        quick_ref.append("godaddy dns delete example.com --name old --type A")
        quick_ref.append("")
        quick_ref.append("# Bulk Operations")
        quick_ref.append("godaddy bulk export example.com --format csv")
        quick_ref.append("godaddy bulk import example.com --file records.csv")
        quick_ref.append("")
        quick_ref.append("# Templates")
        quick_ref.append("godaddy template list                 # Show available templates")
        quick_ref.append("godaddy template apply example.com web-app --var ip=1.2.3.4")
        quick_ref.append("```")
        quick_ref.append("")

        quick_ref.append("## Common Record Types")
        quick_ref.append("")
        quick_ref.append("| Type | Purpose | Example |")
        quick_ref.append("|------|---------|---------|")
        quick_ref.append("| A | IPv4 address | `192.168.1.1` |")
        quick_ref.append("| AAAA | IPv6 address | `2001:db8::1` |")
        quick_ref.append("| CNAME | Alias to another domain | `example.com` |")
        quick_ref.append("| MX | Mail server | `mail.example.com` (priority: 10) |")
        quick_ref.append("| TXT | Text data | `\"v=spf1 mx ~all\"` |")
        quick_ref.append("| SRV | Service location | `10 5 443 service.example.com` |")
        quick_ref.append("")

        quick_ref_file = docs_dir / 'quick_reference.md'
        quick_ref_file.write_text('\n'.join(quick_ref), encoding='utf-8')


if __name__ == '__main__':
    generator = DocGenerator()
    generator.generate()