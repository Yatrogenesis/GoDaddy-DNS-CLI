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
        Decodes GoDaddy API error responses for intelligent guidance

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

            # Handle specific GoDaddy API error codes
            if api_code == 'DOMAIN_NOT_FOUND':
                raise UserFriendlyErrorHandler._handle_domain_not_found_error(domain, api_message)
            elif api_code == 'RECORD_NOT_FOUND':
                raise UserFriendlyErrorHandler._handle_record_not_found_error(domain, record_name, record_type, api_message)
            elif api_code == 'INVALID_IP_ADDRESS':
                raise UserFriendlyErrorHandler._handle_invalid_ip_error(api_message, context)
            elif api_code == 'INVALID_DOMAIN':
                raise UserFriendlyErrorHandler._handle_invalid_domain_error(domain, api_message)
            elif api_code == 'DUPLICATE_RECORD':
                raise UserFriendlyErrorHandler._handle_duplicate_record_error(domain, record_name, record_type, api_message)
            elif api_code == 'QUOTA_EXCEEDED':
                raise UserFriendlyErrorHandler._handle_quota_exceeded_error(api_message)
            elif 'TTL' in api_code.upper():
                raise UserFriendlyErrorHandler._handle_ttl_error(api_message, context)

        except ValueError:
            # Not JSON, try to parse text response
            api_message = response.text or f"HTTP {response.status_code}"
            api_code = 'HTTP_ERROR'

            # Look for common patterns in text responses
            if 'domain not found' in api_message.lower():
                raise UserFriendlyErrorHandler._handle_domain_not_found_error(domain, api_message)
            elif 'record not found' in api_message.lower():
                raise UserFriendlyErrorHandler._handle_record_not_found_error(domain, record_name, record_type, api_message)

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


    @staticmethod
    def _handle_domain_not_found_error(domain: str, api_message: str) -> Exception:
        """Handle domain not found with specific guidance"""
        return DomainNotFoundError(
            f"GoDaddy reported that domain '{domain}' is not found in your account.\n\n"
            f"Possible solutions:\n"
            f"1. Check the domain spelling: '{domain}'\n"
            f"2. Verify the domain is registered with your GoDaddy account\n"
            f"3. Make sure you're using the correct API credentials\n"
            f"4. Check if domain is in a different GoDaddy account\n\n"
            f"To verify: Run 'godaddy domains list' to see all your domains.\n"
            f"GoDaddy API response: {api_message}"
        )

    @staticmethod
    def _handle_record_not_found_error(domain: str, record_name: str, record_type: str, api_message: str) -> Exception:
        """Handle DNS record not found with specific guidance"""
        return RecordNotFoundError(
            f"GoDaddy reported that the {record_type} record '{record_name}' was not found for domain '{domain}'.\n\n"
            f"What you can do:\n"
            f"1. List existing records: 'godaddy dns list {domain}'\n"
            f"2. Check the record name spelling: '{record_name}'\n"
            f"3. Verify the record type: '{record_type}'\n"
            f"4. Create the record if it doesn't exist: 'godaddy dns add {domain} --name {record_name} --type {record_type}'\n\n"
            f"GoDaddy API response: {api_message}"
        )

    @staticmethod
    def _handle_invalid_ip_error(api_message: str, context: Dict[str, Any]) -> Exception:
        """Handle invalid IP address with specific guidance"""
        record_data = context.get('record_data', 'the provided IP')
        return ValidationError(
            f"GoDaddy rejected the IP address: {record_data}\n\n"
            f"IP address requirements:\n"
            f"• IPv4 format: 192.168.1.1 (four numbers 0-255 separated by dots)\n"
            f"• IPv6 format: 2001:db8::1 (hexadecimal groups separated by colons)\n"
            f"• No spaces or special characters\n"
            f"• Must be a valid public IP address\n\n"
            f"Examples of valid IPs:\n"
            f"• IPv4: 1.2.3.4, 192.168.1.100, 10.0.0.1\n"
            f"• IPv6: 2001:db8::1, ::1, fe80::1\n\n"
            f"GoDaddy API response: {api_message}"
        )

    @staticmethod
    def _handle_invalid_domain_error(domain: str, api_message: str) -> Exception:
        """Handle invalid domain format with specific guidance"""
        return ValidationError(
            f"GoDaddy rejected the domain format: '{domain}'\n\n"
            f"Domain format requirements:\n"
            f"• Must be a valid domain name (e.g., example.com)\n"
            f"• Can contain letters, numbers, and hyphens\n"
            f"• Cannot start or end with a hyphen\n"
            f"• Must have a valid TLD (.com, .org, .net, etc.)\n"
            f"• Maximum 253 characters total\n\n"
            f"Examples of valid domains:\n"
            f"• example.com, my-site.org, test123.net\n\n"
            f"GoDaddy API response: {api_message}"
        )

    @staticmethod
    def _handle_duplicate_record_error(domain: str, record_name: str, record_type: str, api_message: str) -> Exception:
        """Handle duplicate record with specific guidance"""
        return ConflictError(
            f"GoDaddy reported that a {record_type} record for '{record_name}' already exists in domain '{domain}'.\n\n"
            f"Your options:\n"
            f"1. Update the existing record: 'godaddy dns update {domain} --name {record_name} --type {record_type} --data [new-value]'\n"
            f"2. Delete the existing record first: 'godaddy dns delete {domain} --name {record_name} --type {record_type}'\n"
            f"3. View current records: 'godaddy dns list {domain} --name {record_name}'\n\n"
            f"Note: Some record types (like CNAME) can only have one instance per name.\n"
            f"GoDaddy API response: {api_message}"
        )

    @staticmethod
    def _handle_quota_exceeded_error(api_message: str) -> Exception:
        """Handle quota exceeded with specific guidance"""
        return APIError(
            f"GoDaddy API quota exceeded - you've reached your rate limit.\n\n"
            f"What this means:\n"
            f"• You've made too many API requests in a short time\n"
            f"• GoDaddy limits requests to prevent abuse\n"
            f"• This is temporary and will reset automatically\n\n"
            f"What you can do:\n"
            f"1. Wait a few minutes before trying again\n"
            f"2. Use bulk operations for multiple changes\n"
            f"3. Reduce the frequency of your requests\n"
            f"4. Consider using '--delay' option for batch operations\n\n"
            f"GoDaddy API response: {api_message}"
        )

    @staticmethod
    def _handle_ttl_error(api_message: str, context: Dict[str, Any]) -> Exception:
        """Handle TTL-related errors with specific guidance"""
        ttl_value = context.get('ttl', 'the provided TTL')
        return ValidationError(
            f"GoDaddy rejected the TTL (Time To Live) value: {ttl_value}\n\n"
            f"TTL requirements:\n"
            f"• Must be between 300 seconds (5 minutes) and 604800 seconds (7 days)\n"
            f"• Common values: 300 (5 min), 3600 (1 hour), 86400 (24 hours)\n"
            f"• Lower values = faster updates, higher DNS query load\n"
            f"• Higher values = slower updates, lower DNS query load\n\n"
            f"Recommended TTL values:\n"
            f"• 300s: During DNS changes/migrations\n"
            f"• 3600s: Standard for most records\n"
            f"• 86400s: Stable records that rarely change\n\n"
            f"GoDaddy API response: {api_message}"
        )


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