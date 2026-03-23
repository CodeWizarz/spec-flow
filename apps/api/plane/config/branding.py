"""
SpecFlow Branding Configuration
"""

APP_NAME = "SpecFlow"
APP_NAME_LOWER = "specflow"
APP_DESCRIPTION = "Autonomous Product Development System"
APP_TAGLINE = "Self-improving autonomous feature builder"

# Company/Project Info
COMPANY_NAME = "SpecFlow"
COPYRIGHT_YEAR = "2026"

# URLs
DOCS_URL = "https://specflow.ai/docs"
SUPPORT_URL = "https://specflow.ai/support"

# Branding Colors
PRIMARY_COLOR = "#6366F1"  # Indigo
ACCENT_COLOR = "#8B5CF6"    # Purple

# Version
VERSION = "1.0.0"
BUILD_DATE = "2026-03-23"

def get_app_info():
    """Return full app info dict."""
    return {
        "name": APP_NAME,
        "description": APP_DESCRIPTION,
        "tagline": APP_TAGLINE,
        "version": VERSION,
    }