"""
GoDaddy DNS CLI - Enterprise Setup Configuration
Enterprise-grade CLI tool for GoDaddy DNS management
"""

from setuptools import setup, find_packages
import os
import sys

# Read version from version file
version_file = os.path.join(os.path.dirname(__file__), 'godaddy_cli', '__version__.py')
version_dict = {}
if os.path.exists(version_file):
    with open(version_file) as f:
        exec(f.read(), version_dict)
    VERSION = version_dict.get('__version__', '1.0.0')
else:
    VERSION = '1.0.0'

# Read README for long description
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Core dependencies
install_requires = [
    'click>=8.0.0',
    'requests>=2.28.0',
    'rich>=13.0.0',
    'pyyaml>=6.0',
    'tabulate>=0.9.0',
    'python-dotenv>=1.0.0',
    'cryptography>=41.0.0',
    'jsonschema>=4.0.0',
    'aiohttp>=3.8.0',
    'asyncio>=3.4.3',
    'dnspython>=2.3.0',
    'validators>=0.20.0',
    'toml>=0.10.2',
    'jinja2>=3.1.0',
    'watchdog>=3.0.0',
    'keyring>=24.0.0',
    'colorama>=0.4.6;platform_system=="Windows"',
]

# Development dependencies
dev_requires = [
    'pytest>=7.0.0',
    'pytest-asyncio>=0.21.0',
    'pytest-cov>=4.0.0',
    'pytest-mock>=3.10.0',
    'black>=23.0.0',
    'flake8>=6.0.0',
    'mypy>=1.0.0',
    'isort>=5.12.0',
    'pre-commit>=3.0.0',
    'tox>=4.0.0',
    'sphinx>=6.0.0',
    'sphinx-rtd-theme>=1.2.0',
    'wheel>=0.40.0',
    'twine>=4.0.0',
]

# Web UI dependencies
web_requires = [
    'fastapi>=0.100.0',
    'uvicorn>=0.23.0',
    'websockets>=11.0.0',
    'jinja2>=3.1.0',
    'python-multipart>=0.0.6',
    'aiofiles>=23.0.0',
]

setup(
    name='godaddy-dns-cli',
    version=VERSION,
    author='Yatrogenesis',
    author_email='support@godaddy-cli.dev',
    description='Enterprise-grade CLI tool for GoDaddy DNS management - Like wrangler but for GoDaddy',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Yatrogenesis/GoDaddy-DNS-CLI',
    project_urls={
        'Documentation': 'https://godaddy-cli.dev/docs',
        'Bug Reports': 'https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/issues',
        'Source': 'https://github.com/Yatrogenesis/GoDaddy-DNS-CLI',
        'Changelog': 'https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/blob/main/CHANGELOG.md',
    },
    packages=find_packages(exclude=['tests*', 'docs*', 'examples*']),
    include_package_data=True,
    package_data={
        'godaddy_cli': [
            'templates/*',
            'static/*',
            'web/dist/*',
        ],
    },
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires,
        'web': web_requires,
        'all': install_requires + dev_requires + web_requires,
    },
    entry_points={
        'console_scripts': [
            'godaddy=godaddy_cli.cli:main',
            'gd=godaddy_cli.cli:main',  # Short alias
            'godaddy-web=godaddy_cli.web.server:main',  # Web UI
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Internet :: Name Service (DNS)',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Environment :: Web Environment',
    ],
    python_requires='>=3.8',
    keywords='godaddy dns cli automation devops infrastructure api management',
    zip_safe=False,
)