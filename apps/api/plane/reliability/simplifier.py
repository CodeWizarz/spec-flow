import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SpecSimplifier:
    """Transforms complex specs into minimal viable implementations."""
    
    @classmethod
    def simplify(cls, spec_json: Dict[str, Any]) -> Dict[str, Any]:
        """Reduce spec to minimal viable implementation"""
        
        simplified = spec_json.copy()
        
        # Reduce tasks to essential actions only
        tasks = simplified.get('tasks', [])
        if tasks:
            simplified['tasks'] = cls._simplify_tasks(tasks)
        
        # Simplify UI changes
        ui_changes = simplified.get('ui_changes', [])
        if ui_changes:
            simplified['ui_changes'] = ui_changes[:2]  # Max 2 changes
        
        # Clear complex workflow changes
        simplified['workflow_changes'] = []
        
        # Simplify solution description
        solution = simplified.get('solution', '')
        if len(solution) > 200:
            simplified['solution'] = solution[:200] + '...'
        
        # Add simplification marker
        simplified['_simplified'] = True
        
        logger.info(f"Spec simplified from {len(tasks)} tasks to {len(simplified.get('tasks', []))}")
        
        return simplified
    
    @classmethod
    def _simplify_tasks(cls, tasks: List[Dict]) -> List[Dict]:
        """Reduce tasks to essential actions only"""
        
        simplified_tasks = []
        for task in tasks:
            simplified_task = task.copy()
            
            # Reduce action list to first 2 items
            actions = simplified_task.get('action', [])
            if len(actions) > 2:
                simplified_task['action'] = actions[:2]
            
            # Limit read_first files to 1
            read_first = simplified_task.get('read_first', [])
            if len(read_first) > 1:
                simplified_task['read_first'] = read_first[:1]
            
            simplified_tasks.append(simplified_task)
        
        # Limit total tasks to 2
        return simplified_tasks[:2]
    
    @classmethod
    def simplify_for_retry(cls, spec_json: Dict[str, Any], failure_type: str) -> Dict[str, Any]:
        """Aggressively simplify spec based on failure type"""
        
        simplified = spec_json.copy()
        
        # Remove problematic elements based on failure type
        if failure_type in ['syntax_error', 'logic_error']:
            # Remove all file dependencies
            for task in simplified.get('tasks', []):
                task['read_first'] = []
        
        elif failure_type == 'test_failure':
            # Simplify solution to basic implementation
            simplified['solution'] = 'Simple implementation of core functionality.'
            simplified['tasks'] = simplified.get('tasks', [])[:1]
        
        elif failure_type == 'missing_dependency':
            # Remove any external dependencies
            simplified['data_model_changes'] = []
        
        elif failure_type == 'unclear_spec':
            # Create minimal placeholder spec
            simplified['tasks'] = [{'read_first': [], 'action': ['Create basic feature implementation']}]
        
        simplified['_retry_simplified'] = True
        
        return simplified