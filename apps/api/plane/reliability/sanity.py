import logging
import ast

logger = logging.getLogger(__name__)

class SanityChecker:
    """Run correctness checks before marking success."""
    
    @classmethod
    def run_sanity_checks(cls, generated_files: dict, spec_json: dict) -> dict:
        """Run sanity checks and return results."""
        
        results = {
            'passed': True,
            'checks': [],
            'warnings': []
        }
        
        # Check 1: Files exist
        if not generated_files:
            results['passed'] = False
            results['checks'].append(('files_exist', False, 'No files generated'))
            return results
        
        results['checks'].append(('files_exist', True, f'{len(generated_files)} files generated'))
        
        # Check 2: Python syntax validity
        syntax_ok = cls._check_syntax(generated_files)
        results['checks'].append(('syntax_valid', syntax_ok, 'Python syntax valid' if syntax_ok else 'Syntax errors found'))
        results['passed'] = results['passed'] and syntax_ok
        
        # Check 3: Code has content
        content_ok = cls._check_content(generated_files)
        results['checks'].append(('has_content', content_ok, 'Files have content' if content_ok else 'Files are empty'))
        results['passed'] = results['passed'] and content_ok
        
        # Check 4: Has function/class definitions
        definitions_ok = cls._check_definitions(generated_files)
        results['checks'].append(('has_definitions', definitions_ok, 'Has definitions' if definitions_ok else 'No definitions found'))
        results['passed'] = results['passed'] and definitions_ok
        
        # Check 5: Spec has required fields
        spec_ok = cls._check_spec(spec_json)
        results['checks'].append(('spec_valid', spec_ok, 'Spec valid' if spec_ok else 'Spec incomplete'))
        results['passed'] = results['passed'] and spec_ok
        
        # Check 6: Consistency with solution
        solution_ok = cls._check_solution_match(generated_files, spec_json)
        results['checks'].append(('solution_match', solution_ok, 'Code matches solution intent' if solution_ok else 'Code may not match solution'))
        
        logger.info(f"Sanity check results: {results}")
        
        return results
    
    @classmethod
    def _check_syntax(cls, generated_files: dict) -> bool:
        """Check all Python files have valid syntax."""
        for filepath, content in generated_files.items():
            if filepath.endswith('.py'):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    logger.error(f"Syntax error in {filepath}: {e}")
                    return False
        return True
    
    @classmethod
    def _check_content(cls, generated_files: dict) -> bool:
        """Check files have actual content."""
        for filepath, content in generated_files.items():
            if len(content.strip()) < 20:
                logger.warning(f"File {filepath} is too small")
                return False
        return True
    
    @classmethod
    def _check_definitions(cls, generated_files: dict) -> bool:
        """Check files have function/class definitions."""
        for filepath, content in generated_files.items():
            if filepath.endswith('.py'):
                if 'def ' not in content and 'class ' not in content:
                    logger.warning(f"File {filepath} has no definitions")
                    return False
        return True
    
    @classmethod
    def _check_spec(cls, spec_json: dict) -> bool:
        """Check spec has required fields."""
        required = ['feature_name', 'solution']
        for field in required:
            if field not in spec_json or not spec_json[field]:
                return False
        return True
    
    @classmethod
    def _check_solution_match(cls, generated_files: dict, spec_json: dict) -> bool:
        """Check code aligns with solution description."""
        solution = spec_json.get('solution', '').lower()
        
        # If solution mentions specific tech, check it's present
        tech_indicators = {
            'model': 'class ',
            'api': 'def ', 
            'view': 'def ',
            'component': 'return',
            'endpoint': 'def ',
        }
        
        for keyword, pattern in tech_indicators.items():
            if keyword in solution:
                found = any(pattern in content for content in generated_files.values())
                if not found:
                    logger.warning(f"Solution mentions '{keyword}' but no matching pattern found")
        
        return True
    
    @classmethod
    def determine_outcome(cls, sanity_results: dict, test_result: dict, execution_log: list) -> str:
        """Determine outcome: success, partial_success, or failure."""
        
        if not sanity_results['passed']:
            return 'failure'
        
        if test_result.get('returncode', 0) == 0:
            # All checks passed
            return 'success'
        
        # Check if only minor issues
        errors = test_result.get('stdout', '')
        if 'warning' in errors.lower() or 'deprecated' in errors.lower():
            return 'partial_success'
        
        return 'failure'