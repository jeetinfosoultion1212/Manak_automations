import os
import sys

# Database Configuration
# IMPORTANT: Use environment variables instead of hardcoding credentials
# Set these environment variables on your system:
#   DB_HOST=your_host
#   DB_DATABASE=your_database
#   DB_USER=your_username
#   DB_PASSWORD=your_password
#   API_BASE_URL=your_api_url

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_DATABASE', 'manak_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '')  # Use environment variable!
}

# API Configuration - Load from environment variable or use default
# Set API_BASE_URL environment variable for production
API_BASE_URL = os.getenv('API_BASE_URL', 'https://hallmarkpro.in/admin/')
if not API_BASE_URL.endswith('/'):
    API_BASE_URL += '/'

JEWELLER_API_URL = API_BASE_URL + "get_jewellers_api.php"
CHECK_JOBS_API_URL = API_BASE_URL + "check_jobs_api.php"
MANAGE_JEWELLER_API_URL = API_BASE_URL + "manage_jeweller_api.php"
SAVE_JOB_API_URL = API_BASE_URL + "save_job_api.php"
REPORT_API_URL = API_BASE_URL + "get_report_by_id.php"
GET_JOBS_API_URL = API_BASE_URL + "get_jobs_api.php"
REQUEST_API_URL = API_BASE_URL + "API/get_request_no.php"
BILL_IMPORT_API_URL = API_BASE_URL + "bill_import_api.php"

# Application Configuration
APP_CONFIG = {
    'version': '10.0',
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
