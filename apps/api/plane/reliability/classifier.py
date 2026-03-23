import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ComplexityClassifier:
    """Classifies specs into simple/medium/complex to determine execution eligibility."""
    
    COMPLEX_KEYWORDS = [
        'multi', 'system', 'integration', 'external', 'api', 'auth', 'payment',
        'workflow', 'async', 'queue', 'migration', 'refactor', 'performance',
        'security', 'analytics', 'reporting', 'export', 'import', 'batch',
        'cron', 'webhook', 'socket', 'streaming', 'cache', 'optimization'
    ]
    
    SIMPLE_KEYWORDS = [
        'add', 'create', 'update', 'delete', 'view', 'list', 'display',
        'show', 'enable', 'disable', 'flag', 'toggle', 'field', 'label',
        'text', 'button', 'link', 'icon', 'color', 'size', 'simple'
    ]
    
    @classmethod
    def classify(cls, spec_json: Dict[str, Any]) -> str:
        """Classify spec complexity: simple, medium, or complex"""
        
        feature_name = spec_json.get('feature_name', '').lower()
        solution = spec_json.get('solution', '').lower()
        problem = spec_json.get('problem', '').lower()
        tasks = spec_json.get('tasks', [])
        
        text = f"{feature_name} {solution} {problem}"
        
        # Check for complex indicators
        complex_count = sum(1 for kw in cls.COMPLEX_KEYWORDS if kw in text)
        
        # Check for simple indicators
        simple_count = sum(1 for kw in cls.SIMPLE_KEYWORDS if kw in text)
        
        # Task complexity
        task_count = len(tasks)
        
        # Data model changes indicate complexity
        data_changes = len(spec_json.get('data_model_changes', []))
        
        # Determine classification
        score = (complex_count * 2) - simple_count + (task_count * 0.3) + (data_changes * 0.5)
        
        if complex_count >= 2 or task_count > 4 or data_changes > 2:
            return 'complex'
        elif complex_count >= 1 or task_count > 2 or data_changes > 0:
            return 'medium'
        else:
            return 'simple'
    
    @classmethod
    def can_execute(cls, spec_json: Dict[str, Any]) -> bool:
        """Returns True if spec is simple enough to execute"""
        return cls.classify(spec_json) == 'simple'
    
    @classmethod
    def get_execution_recommendation(cls, spec_json: Dict[str, Any]) -> Dict[str, Any]:
        """Returns recommendation for execution"""
        classification = cls.classify(spec_json)
        
        if classification == 'simple':
            return {
                'can_execute': True,
                'classification': classification,
                'recommendation': 'Execute directly'
            }
        elif classification == 'medium':
            return {
                'can_execute': False,
                'classification': classification,
                'recommendation': 'Simplify before execution'
            }
        else:
            return {
                'can_execute': False,
                'classification': classification,
                'recommendation': 'Defer to future iteration'
            }