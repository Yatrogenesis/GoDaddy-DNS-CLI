"""
Validation utilities for DNS records and configuration
"""

import re
import ipaddress
from typing import List, Optional
from urllib.parse import urlparse

from godaddy_cli.core.exceptions import ValidationError


def validate_domain(domain: str) -> bool:
    """
    Validate domain name format

    Args:
        domain: Domain name to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If domain is invalid
    """
    if not domain:
        raise ValidationError("Domain cannot be empty")

    if len(domain) > 253:
        raise ValidationError("Domain name too long (max 253 characters)")

    if domain.endswith('.'):
        domain = domain[:-1]

    # Check for valid characters and structure
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    if not re.match(pattern, domain):
        raise ValidationError(f"Invalid domain format: {domain}")

    # Check each label
    labels = domain.split('.')
    for label in labels:
        if len(label) > 63:
            raise ValidationError(f"Domain label too long: {label}")
        if label.startswith('-') or label.endswith('-'):
            raise ValidationError(f"Domain label cannot start or end with hyphen: {label}")

    return True


def validate_subdomain(subdomain: str) -> bool:
    """
    Validate subdomain/record name format

    Args:
        subdomain: Subdomain name to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If subdomain is invalid
    """
    if not subdomain:
        raise ValidationError("Subdomain cannot be empty")

    # Allow @ for root domain
    if subdomain == '@':
        return True

    # Allow wildcard
    if subdomain == '*':
        return True

    if len(subdomain) > 63:
        raise ValidationError("Subdomain too long (max 63 characters)")

    # Check for valid characters
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-_]{0,61}[a-zA-Z0-9])?$'
    if not re.match(pattern, subdomain):
        raise ValidationError(f"Invalid subdomain format: {subdomain}")

    if subdomain.startswith('-') or subdomain.endswith('-'):
        raise ValidationError("Subdomain cannot start or end with hyphen")

    return True


def validate_ip(ip: str, version: Optional[int] = None) -> bool:
    """
    Validate IP address format

    Args:
        ip: IP address to validate
        version: IP version (4 or 6), None for auto-detect

    Returns:
        True if valid

    Raises:
        ValidationError: If IP is invalid
    """
    if not ip:
        raise ValidationError("IP address cannot be empty")

    try:
        addr = ipaddress.ip_address(ip)

        if version and addr.version != version:
            raise ValidationError(f"Expected IPv{version}, got IPv{addr.version}")

        return True
    except ValueError as e:
        raise ValidationError(f"Invalid IP address: {ip} - {str(e)}")


def validate_ttl(ttl: int) -> bool:
    """
    Validate TTL value

    Args:
        ttl: TTL value in seconds

    Returns:
        True if valid

    Raises:
        ValidationError: If TTL is invalid
    """
    if not isinstance(ttl, int):
        raise ValidationError("TTL must be an integer")

    if ttl < 300:
        raise ValidationError("TTL must be at least 300 seconds (5 minutes)")

    if ttl > 86400:
        raise ValidationError("TTL must be at most 86400 seconds (24 hours)")

    return True


def validate_priority(priority: int) -> bool:
    """
    Validate priority value for MX/SRV records

    Args:
        priority: Priority value

    Returns:
        True if valid

    Raises:
        ValidationError: If priority is invalid
    """
    if not isinstance(priority, int):
        raise ValidationError("Priority must be an integer")

    if priority < 0 or priority > 65535:
        raise ValidationError("Priority must be between 0 and 65535")

    return True


def validate_port(port: int) -> bool:
    """
    Validate port number for SRV records

    Args:
        port: Port number

    Returns:
        True if valid

    Raises:
        ValidationError: If port is invalid
    """
    if not isinstance(port, int):
        raise ValidationError("Port must be an integer")

    if port < 1 or port > 65535:
        raise ValidationError("Port must be between 1 and 65535")

    return True


def validate_weight(weight: int) -> bool:
    """
    Validate weight value for SRV records

    Args:
        weight: Weight value

    Returns:
        True if valid

    Raises:
        ValidationError: If weight is invalid
    """
    if not isinstance(weight, int):
        raise ValidationError("Weight must be an integer")

    if weight < 0 or weight > 65535:
        raise ValidationError("Weight must be between 0 and 65535")

    return True


def validate_record_type(record_type: str) -> bool:
    """
    Validate DNS record type

    Args:
        record_type: DNS record type

    Returns:
        True if valid

    Raises:
        ValidationError: If record type is invalid
    """
    valid_types = {
        'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'NS', 'PTR', 'CAA'
    }

    if record_type.upper() not in valid_types:
        raise ValidationError(f"Invalid record type: {record_type}. Valid types: {', '.join(valid_types)}")

    return True


def validate_cname_data(data: str) -> bool:
    """
    Validate CNAME record data

    Args:
        data: CNAME target

    Returns:
        True if valid

    Raises:
        ValidationError: If CNAME data is invalid
    """
    if not data:
        raise ValidationError("CNAME data cannot be empty")

    # CNAME must point to a valid hostname
    validate_domain(data)
    return True


def validate_mx_data(data: str) -> bool:
    """
    Validate MX record data

    Args:
        data: MX target hostname

    Returns:
        True if valid

    Raises:
        ValidationError: If MX data is invalid
    """
    if not data:
        raise ValidationError("MX data cannot be empty")

    # MX must point to a valid hostname
    validate_domain(data)
    return True


def validate_txt_data(data: str) -> bool:
    """
    Validate TXT record data

    Args:
        data: TXT record content

    Returns:
        True if valid

    Raises:
        ValidationError: If TXT data is invalid
    """
    if not data:
        raise ValidationError("TXT data cannot be empty")

    if len(data) > 255:
        raise ValidationError("TXT record data too long (max 255 characters)")

    return True


def validate_srv_data(data: str) -> bool:
    """
    Validate SRV record data

    Args:
        data: SRV target hostname

    Returns:
        True if valid

    Raises:
        ValidationError: If SRV data is invalid
    """
    if not data:
        raise ValidationError("SRV data cannot be empty")

    # SRV must point to a valid hostname
    validate_domain(data)
    return True


def validate_url(url: str) -> bool:
    """
    Validate URL format

    Args:
        url: URL to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If URL is invalid
    """
    if not url:
        raise ValidationError("URL cannot be empty")

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValidationError("Invalid URL format")

        if result.scheme not in ['http', 'https']:
            raise ValidationError("URL must use http or https scheme")

        return True
    except Exception as e:
        raise ValidationError(f"Invalid URL: {str(e)}")


def validate_email(email: str) -> bool:
    """
    Validate email address format

    Args:
        email: Email address to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If email is invalid
    """
    if not email:
        raise ValidationError("Email cannot be empty")

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email format: {email}")

    return True


def validate_batch_size(batch_size: int) -> bool:
    """
    Validate batch size for bulk operations

    Args:
        batch_size: Batch size

    Returns:
        True if valid

    Raises:
        ValidationError: If batch size is invalid
    """
    if not isinstance(batch_size, int):
        raise ValidationError("Batch size must be an integer")

    if batch_size < 1:
        raise ValidationError("Batch size must be at least 1")

    if batch_size > 100:
        raise ValidationError("Batch size must be at most 100")

    return True


def validate_file_path(file_path: str) -> bool:
    """
    Validate file path format

    Args:
        file_path: File path to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If file path is invalid
    """
    if not file_path:
        raise ValidationError("File path cannot be empty")

    # Check for dangerous characters
    dangerous_chars = ['..', '\\', '|', ';', '&']
    for char in dangerous_chars:
        if char in file_path:
            raise ValidationError(f"File path contains dangerous character: {char}")

    return True