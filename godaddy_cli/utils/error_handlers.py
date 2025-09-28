"""
Enhanced error handling utilities for user-friendly CLI experience
"""

import requests
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from godaddy_cli.core.exceptions import (
    APIError, AuthenticationError, RecordNotFoundError, DomainNotFoundError,
    ValidationError, RateLimitError, BadRequestError, ForbiddenError,
    ConflictError, ServerError, NetworkError, TimeoutError
)

console = Console()


class UserFriendlyErrorHandler:
    """Enhanced error handler with specific user guidance"""

    @staticmethod
    def handle_api_response_error(response: requests.Response, context: Dict[str, Any] = None) -> None:
        """
        Handle API response errors with specific user-friendly messages

        Args:
            response: HTTP response object
            context: Additional context about the operation
        """
        context = context or {}
        domain = context.get('domain')
        record_name = context.get('record_name')
        record_type = context.get('record_type')
        operation = context.get('operation', 'API operation')

        try:
            error_data = response.json()
            api_message = error_data.get('message', 'Unknown error')
            api_code = error_data.get('code', 'UNKNOWN')
        except:
            api_message = response.text or f"HTTP {response.status_code}"
            api_code = 'HTTP_ERROR'

        # Handle specific status codes with enhanced messages
        if response.status_code == 400:
            raise UserFriendlyErrorHandler._handle_bad_request(api_message, api_code, context)
        elif response.status_code == 401:
            raise UserFriendlyErrorHandler._handle_authentication_error(api_message, context)
        elif response.status_code == 403:
            raise UserFriendlyErrorHandler._handle_forbidden_error(api_message, context)
        elif response.status_code == 404:
            raise UserFriendlyErrorHandler._handle_not_found_error(api_message, context)
        elif response.status_code == 409:
            raise UserFriendlyErrorHandler._handle_conflict_error(api_message, context)
        elif response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise UserFriendlyErrorHandler._handle_rate_limit_error(api_message, retry_after, context)
        elif response.status_code >= 500:
            raise UserFriendlyErrorHandler._handle_server_error(api_message, context)
        else:
            raise APIError(f"Unexpected API error: {api_message}", response.status_code)

    @staticmethod
    def _handle_bad_request(api_message: str, api_code: str, context: Dict[str, Any]) -> Exception:
        """Handle 400 Bad Request errors with specific guidance"""
        domain = context.get('domain')
        record_type = context.get('record_type')
        operation = context.get('operation')

        # TTL validation errors
        if 'ttl' in api_message.lower():
            return ValidationError(
                f"Invalid TTL value. TTL must be between 300 and 604800 seconds (5 minutes to 7 days). "
                f"Try using a standard value like 3600 (1 hour) or 86400 (24 hours)."
            )

        # IP address validation errors
        if 'ip' in api_message.lower() or 'address' in api_message.lower():
            return ValidationError(
                f"Invalid IP address format. "
                f"For A records, use IPv4 format (e.g., 192.168.1.1). "
                f"For AAAA records, use IPv6 format (e.g., 2001:db8::1)."
            )

        # Domain name validation errors
        if 'domain' in api_message.lower() or 'name' in api_message.lower():
            return ValidationError(
                f"Invalid domain or record name format. "
                f"Names must contain only letters, numbers, hyphens, and dots. "
                f"Use '@' for the root domain or subdomain names like 'www' or 'api'."
            )

        # Record type validation
        if 'type' in api_message.lower():
            return ValidationError(
                f"Invalid record type. "
                f"Supported types: A, AAAA, CNAME, MX, TXT, SRV, NS, PTR. "
                f"Use 'godaddy dns add {domain or '[domain]'} --help' for examples."
            )

        # Priority/Weight validation for MX/SRV records
        if 'priority' in api_message.lower() or 'weight' in api_message.lower():
            return ValidationError(
                f"Invalid priority or weight value for {record_type or 'MX/SRV'} record. "
                f"Priority should be 0-65535, with lower values having higher priority. "
                f"Common MX priorities: 10 (primary), 20 (backup)."
            )

        return BadRequestError(f"Invalid request: {api_message}")

    @staticmethod
    def _handle_authentication_error(api_message: str, context: Dict[str, Any]) -> Exception:
        """Handle authentication errors with setup guidance"""
        return AuthenticationError(
            f"Authentication failed. Your API credentials may be invalid or expired.\n\n"
            f"To fix this:\n"
            f"1. Verify your API key and secret at https://developer.godaddy.com/keys\n"
            f"2. Run 'godaddy auth setup' to update your credentials\n"
            f"3. Make sure your API key has the correct permissions\n\n"
            f"API Response: {api_message}"
        )

    @staticmethod
    def _handle_forbidden_error(api_message: str, context: Dict[str, Any]) -> Exception:
        """Handle forbidden errors with permission guidance"""
        domain = context.get('domain')
        operation = context.get('operation')

        return ForbiddenError(
            f"Access denied. You don't have permission to perform this operation.\n\n"
            f"Possible causes:\n"
            f"1. Domain '{domain}' is not in your GoDaddy account\n"
            f"2. Your API key doesn't have sufficient permissions\n"
            f"3. Domain is locked or has restrictions\n\n"
            f"To fix this:\n"
            f"1. Verify domain ownership in your GoDaddy account\n"
            f"2. Check API key permissions at https://developer.godaddy.com/keys\n"
            f"3. Contact GoDaddy support if domain appears locked\n\n"
            f"API Response: {api_message}"
        )

    @staticmethod
    def _handle_not_found_error(api_message: str, context: Dict[str, Any]) -> Exception:
        """Handle not found errors with specific guidance"""
        domain = context.get('domain')
        record_name = context.get('record_name')
        record_type = context.get('record_type')
        operation = context.get('operation')

        # Domain not found
        if operation == 'get_domains' or 'domain' in api_message.lower():
            return DomainNotFoundError(domain or 'unknown')

        # DNS record not found
        if operation in ['get_records', 'update_record', 'delete_record']:
            return RecordNotFoundError(domain, record_name, record_type)

        return NotFoundError(f"Resource not found: {api_message}")

    @staticmethod
    def _handle_conflict_error(api_message: str, context: Dict[str, Any]) -> Exception:
        """Handle conflict errors with resolution guidance"""
        domain = context.get('domain')
        record_name = context.get('record_name')
        record_type = context.get('record_type')

        return ConflictError(
            f"Resource conflict detected. A record may already exist.\n\n"
            f"To resolve:\n"
            f"1. Check existing records: 'godaddy dns list {domain or '[domain]'}'\n"
            f"2. Update instead of adding: 'godaddy dns update {domain or '[domain]'} --name {record_name or '[name]'} --type {record_type or '[type]'}'\n"
            f"3. Delete existing record first: 'godaddy dns delete {domain or '[domain]'} --name {record_name or '[name]'} --type {record_type or '[type]'}'\n\n"
            f"API Response: {api_message}"
        )

    @staticmethod
    def _handle_rate_limit_error(api_message: str, retry_after: str, context: Dict[str, Any]) -> Exception:
        """Handle rate limit errors with timing guidance"""
        if retry_after:
            try:
                wait_time = int(retry_after)
                return RateLimitError(
                    f"API rate limit exceeded. Please wait {wait_time} seconds before retrying.\n\n"
                    f"Tips to avoid rate limits:\n"
                    f"1. Use bulk operations for multiple records\n"
                    f"2. Reduce request frequency\n"
                    f"3. Consider using '--delay' option for batch operations\n\n"
                    f"The CLI will automatically retry after the wait period.",
                    wait_time
                )
            except ValueError:
                pass

        return RateLimitError(
            f"API rate limit exceeded. Please wait a few minutes before retrying.\n\n"
            f"Tips to avoid rate limits:\n"
            f"1. Use bulk operations for multiple records\n"
            f"2. Reduce request frequency\n"
            f"3. Consider using '--delay' option for batch operations"
        )

    @staticmethod
    def _handle_server_error(api_message: str, context: Dict[str, Any]) -> Exception:
        """Handle server errors with retry guidance"""
        return ServerError(
            f"GoDaddy API server error. This is usually temporary.\n\n"
            f"To resolve:\n"
            f"1. Wait a few minutes and try again\n"
            f"2. Check GoDaddy status: https://status.godaddy.com\n"
            f"3. If problem persists, contact GoDaddy support\n\n"
            f"API Response: {api_message}"
        )

    @staticmethod
    def handle_network_error(error: Exception, operation: str = "API request") -> NetworkError:
        """Handle network-related errors"""
        if "timeout" in str(error).lower():
            return TimeoutError(
                f"Network timeout during {operation}.\n\n"
                f"To resolve:\n"
                f"1. Check your internet connection\n"
                f"2. Try again in a few moments\n"
                f"3. Use '--timeout' option to increase timeout duration\n\n"
                f"Error: {str(error)}"
            )
        elif "connection" in str(error).lower():
            return NetworkError(
                f"Network connection failed during {operation}.\n\n"
                f"To resolve:\n"
                f"1. Check your internet connection\n"
                f"2. Verify DNS resolution is working\n"
                f"3. Check if a firewall is blocking the connection\n\n"
                f"Error: {str(error)}"
            )
        else:
            return NetworkError(
                f"Network error during {operation}: {str(error)}\n\n"
                f"Please check your internet connection and try again."
            )

    @staticmethod
    def display_error_with_suggestions(error: Exception, show_traceback: bool = False):
        """Display error with rich formatting and suggestions"""
        if isinstance(error, (RecordNotFoundError, DomainNotFoundError)):
            panel_style = "yellow"
            title = "Resource Not Found"
        elif isinstance(error, AuthenticationError):
            panel_style = "red"
            title = "Authentication Error"
        elif isinstance(error, ValidationError):
            panel_style = "orange3"
            title = "Validation Error"
        elif isinstance(error, RateLimitError):
            panel_style = "blue"
            title = "Rate Limit Exceeded"
        elif isinstance(error, NetworkError):
            panel_style = "magenta"
            title = "Network Error"
        else:
            panel_style = "red"
            title = "Error"

        error_text = Text()
        error_text.append(str(error), style="white")

        if show_traceback:
            import traceback
            error_text.append("\n\nFull traceback:\n", style="dim")
            error_text.append(traceback.format_exc(), style="dim red")

        panel = Panel(
            error_text,
            title=f"[bold]{title}[/bold]",
            border_style=panel_style,
            padding=(1, 2)
        )

        console.print(panel)

    @staticmethod
    def suggest_alternative_commands(failed_command: str, domain: str = None):
        """Suggest alternative commands when one fails"""
        suggestions = []

        if "list" in failed_command:
            suggestions.extend([
                f"godaddy domains list  # List all your domains",
                f"godaddy status        # Check configuration"
            ])

        if "add" in failed_command and domain:
            suggestions.extend([
                f"godaddy dns list {domain}     # Check existing records first",
                f"godaddy dns update {domain}   # Update existing record instead"
            ])

        if "delete" in failed_command and domain:
            suggestions.extend([
                f"godaddy dns list {domain}     # Verify record exists",
                f"godaddy dns backup {domain}   # Backup before deletion"
            ])

        if suggestions:
            console.print("\n[bold blue]Suggested alternatives:[/bold blue]")
            for suggestion in suggestions:
                console.print(f"  [dim]$[/dim] [cyan]{suggestion}[/cyan]")


def create_error_context(operation: str, domain: str = None, record_name: str = None,
                        record_type: str = None, **kwargs) -> Dict[str, Any]:
    """Create error context for enhanced error handling"""
    context = {
        'operation': operation,
        'domain': domain,
        'record_name': record_name,
        'record_type': record_type
    }
    context.update(kwargs)
    return {k: v for k, v in context.items() if v is not None}