import logging
from typing import List, Dict, Any
from django.utils import timezone

logger = logging.getLogger(__name__)

class ExecutionTimeline:
    """Create and track execution timeline for transparency."""
    
    @classmethod
    def create_entry(cls, step: str, detail: str = "", status: str = "pending") -> dict:
        """Create a timeline entry."""
        return {
            'step': step,
            'detail': detail,
            'status': status,
            'timestamp': timezone.now().isoformat()
        }
    
    @classmethod
    def build_timeline(cls, spec_json: dict, execution_log: list, outcome: Any = None) -> dict:
        """Build complete execution timeline."""
        
        timeline = {
            'generated_at': timezone.now().isoformat(),
            'feature_name': spec_json.get('feature_name', 'Unknown'),
            'steps': []
        }
        
        # Step 1: Prediction
        timeline['steps'].append(cls.create_entry(
            'prediction',
            f"Predicted failure type: {spec_json.get('predicted_failure_type', 'none')}",
            'completed'
        ))
        
        # Step 2: Complexity classification
        from plane.reliability.classifier import ComplexityClassifier
        classification = ComplexityClassifier.classify(spec_json)
        timeline['steps'].append(cls.create_entry(
            'complexity_classification',
            f"Classified as: {classification}",
            'completed'
        ))
        
        # Step 3: Simplification
        was_simplified = spec_json.get('_simplified', False)
        timeline['steps'].append(cls.create_entry(
            'simplification',
            f"Simplified: {was_simplified}",
            'completed'
        ))
        
        # Step 4: Code generation
        timeline['steps'].append(cls.create_entry(
            'code_generation',
            f"Generated files: {len(spec_json.get('tasks', []))} tasks",
            'completed'
        ))
        
        # Step 5: Validation steps
        for entry in execution_log:
            if isinstance(entry, dict):
                timeline['steps'].append(cls.create_entry(
                    entry.get('step', 'unknown'),
                    entry.get('detail', ''),
                    'completed'
                ))
        
        # Step 6: Final outcome
        if outcome:
            timeline['steps'].append(cls.create_entry(
                'outcome',
                f"Result: {outcome.result}, Confidence: {outcome.confidence_score}",
                'completed'
            ))
        
        return timeline
    
    @classmethod
    def format_summary(cls, timeline: dict) -> str:
        """Format timeline as human-readable summary."""
        
        lines = [
            "=" * 60,
            "EXECUTION TIMELINE",
            "=" * 60,
            f"Feature: {timeline.get('feature_name', 'Unknown')}",
            f"Generated: {timeline.get('generated_at', '')}",
            ""
        ]
        
        for step in timeline.get('steps', []):
            status_icon = {
                'pending': '⏳',
                'completed': '✅',
                'failed': '❌'
            }.get(step['status'], '❓')
            
            lines.append(f"{status_icon} {step['step'].upper()}")
            if step.get('detail'):
                lines.append(f"   → {step['detail']}")
            lines.append("")
        
        return "\n".join(lines)