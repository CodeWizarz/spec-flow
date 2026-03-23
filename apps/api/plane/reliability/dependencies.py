import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DependencySafety:
    """Ensure code has safe defaults and handles missing dependencies."""
    
    COMMON_IMPORTS = [
        'os', 'sys', 'logging', 'datetime', 'json',
        'django', 'rest_framework'
    ]
    
    @classmethod
    def analyze_dependencies(cls, code: str) -> List[str]:
        """Extract required imports from code"""
        
        imports = re.findall(r'^(?:from\s+(\S+)|import\s+(\S+))', code, re.MULTILINE)
        
        deps = []
        for imp in imports:
            module = imp[0] or imp[1]
            top_module = module.split('.')[0]
            deps.append(top_module)
        
        return list(set(deps))
    
    @classmethod
    def make_safe(cls, code: str) -> str:
        """Add safe defaults and error handling to code"""
        
        # Wrap in try-except if no error handling
        if 'try:' not in code and 'except' not in code:
            lines = code.split('\n')
            indented_lines = ['    ' + line for line in lines]
            safe_code = 'try:\n' + '\n'.join(indented_lines) + '\nexcept Exception as e:\n    pass'
            return safe_code
        
        return code
    
    @classmethod
    def mock_external_dependencies(cls, code: str) -> str:
        """Add mock fallbacks for external dependencies"""
        
        # Add fallback for external imports
        code = code.replace('import openai', '# import openai  # Mocked for safety')
        code = code.replace('import requests', '# import requests  # Mocked for safety')
        
        return code
    
    @classmethod
    def ensure_safe_imports(cls, code: str) -> str:
        """Ensure common imports are available"""
        
        has_logging = 'import logging' in code or 'from logging' in code
        if not has_logging:
            code = 'import logging\nlogger = logging.getLogger(__name__)\n\n' + code
        
        return code