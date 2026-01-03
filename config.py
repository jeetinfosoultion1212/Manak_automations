"""
Configuration file for MANAK Desktop Application
This file contains sensitive configuration data.
DO NOT commit this file to version control with real credentials.
"""

import os

# Database Configuration
# You can set these as environment variables or modify the defaults here
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '217.21.85.154'),
    'database': os.getenv('DB_DATABASE', 'u176143338_hallmarkProver'),
    'user': os.getenv('DB_USER', 'u176143338_hallmarkProver'),
    'password': os.getenv('DB_PASSWORD', 'Rontik10@')
}

# Application Configuration
APP_CONFIG = {
    'version': '10.04',
    'debug_mode': False,
    'log_level': 'INFO'
}

# Security: Never log sensitive information
def get_safe_db_config_for_logging():
    """Returns database config without sensitive information for logging purposes"""
    return {
        'host': DB_CONFIG['host'],
        'database': DB_CONFIG['database'],
        'user': '***',  # Never log actual username
        'password': '***'  # Never log actual password
    }
