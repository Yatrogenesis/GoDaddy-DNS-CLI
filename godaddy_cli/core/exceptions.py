"""
Custom exceptions for GoDaddy DNS CLI
"""


class GoDaddyDNSError(Exception):
    """Base exception for GoDaddy DNS CLI"""
    pass


class APIError(GoDaddyDNSError):
    """Exception raised for API-related errors"""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self):
        if self.status_code:
            return f"API Error ({self.status_code}): {self.message}"
        return f"API Error: {self.message}"


class AuthenticationError(GoDaddyDNSError):
    """Exception raised for authentication failures"""
    pass


class ValidationError(GoDaddyDNSError):
    """Exception raised for validation failures"""
    pass


class ConfigurationError(GoDaddyDNSError):
    """Exception raised for configuration issues"""
    pass


class NetworkError(GoDaddyDNSError):
    """Exception raised for network-related issues"""
    pass


class TemplateError(GoDaddyDNSError):
    """Exception raised for template processing errors"""
    pass


class RateLimitError(APIError):
    """Exception raised when API rate limit is exceeded"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, status_code=429)

    def __str__(self):
        if self.retry_after:
            return f"Rate Limit Exceeded: {self.message}. Retry after {self.retry_after} seconds."
        return f"Rate Limit Exceeded: {self.message}"


class NotFoundError(APIError):
    """Exception raised when a resource is not found"""

    def __init__(self, message: str, resource_type: str = None):
        self.resource_type = resource_type
        super().__init__(message, status_code=404)


class ConflictError(APIError):
    """Exception raised when there's a conflict with existing resources"""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class ForbiddenError(APIError):
    """Exception raised when access is forbidden"""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, status_code=403)


class BadRequestError(APIError):
    """Exception raised for bad requests"""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class ServerError(APIError):
    """Exception raised for server errors"""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500)


class TimeoutError(NetworkError):
    """Exception raised when operations timeout"""
    pass


class DNSRecordError(GoDaddyDNSError):
    """Exception raised for DNS record-specific errors"""
    pass


class BulkOperationError(GoDaddyDNSError):
    """Exception raised during bulk operations"""

    def __init__(self, message: str, failed_records: list = None, errors: list = None):
        self.failed_records = failed_records or []
        self.errors = errors or []
        super().__init__(message)


class TemplateValidationError(TemplateError):
    """Exception raised for template validation failures"""

    def __init__(self, message: str, template_name: str = None, errors: list = None):
        self.template_name = template_name
        self.errors = errors or []
        super().__init__(message)


class MonitoringError(GoDaddyDNSError):
    """Exception raised for monitoring-related issues"""
    pass


class ImportError(GoDaddyDNSError):
    """Exception raised during import operations"""
    pass


class ExportError(GoDaddyDNSError):
    """Exception raised during export operations"""
    pass


class DeploymentError(GoDaddyDNSError):
    """Exception raised during deployment operations"""

    def __init__(self, message: str, deployment_plan: dict = None):
        self.deployment_plan = deployment_plan
        super().__init__(message)


class BackupError(GoDaddyDNSError):
    """Exception raised during backup operations"""
    pass


class RestoreError(GoDaddyDNSError):
    """Exception raised during restore operations"""
    pass


def handle_api_error(response) -> None:
    """
    Handle API response and raise appropriate exceptions

    Args:
        response: HTTP response object

    Raises:
        Appropriate API exception based on status code
    """
    if response.status_code == 200:
        return

    try:
        error_data = response.json()
        message = error_data.get('message', 'Unknown API error')
    except:
        message = f"HTTP {response.status_code}: {response.reason}"

    if response.status_code == 400:
        raise BadRequestError(message)
    elif response.status_code == 401:
        raise AuthenticationError(message)
    elif response.status_code == 403:
        raise ForbiddenError(message)
    elif response.status_code == 404:
        raise NotFoundError(message)
    elif response.status_code == 409:
        raise ConflictError(message)
    elif response.status_code == 429:
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                retry_after = int(retry_after)
            except ValueError:
                retry_after = None
        raise RateLimitError(message, retry_after)
    elif response.status_code >= 500:
        raise ServerError(message)
    else:
        raise APIError(message, response.status_code)