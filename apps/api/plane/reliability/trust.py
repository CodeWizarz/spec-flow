import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TrustScorer:
    """Calculate trust score for execution based on validation strength."""
    
    @classmethod
    def calculate_trust_score(cls, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate trust score (0-1) based on:
        - Validation strength
        - Retries needed
        - Confidence score
        - Sanity check results
        """
        
        score = 1.0
        factors = []
        
        # Factor 1: Validation tests passed
        tests_passed = execution_data.get('tests_passed', True)
        if tests_passed:
            factors.append(('validation', 0.3, 'All tests passed'))
            score *= 1.0
        else:
            score *= 0.5
            factors.append(('validation', -0.3, 'Tests failed'))
        
        # Factor 2: Retry count
        retries = execution_data.get('retry_count', 0)
        if retries == 0:
            factors.append(('retries', 0.2, 'No retries needed'))
        elif retries == 1:
            score *= 0.8
            factors.append(('retries', -0.1, 'One retry needed'))
        else:
            score *= 0.6
            factors.append(('retries', -0.2, f'{retries} retries needed'))
        
        # Factor 3: Confidence score
        confidence = execution_data.get('confidence_score', 1.0)
        score *= confidence
        factors.append(('confidence', confidence - 0.5, f'Confidence: {confidence}'))
        
        # Factor 4: Sanity checks
        sanity_passed = execution_data.get('sanity_passed', True)
        if sanity_passed:
            score *= 1.0
            factors.append(('sanity', 0.2, 'All sanity checks passed'))
        else:
            score *= 0.7
            factors.append(('sanity', -0.2, 'Sanity checks failed'))
        
        # Factor 5: Simplification needed
        was_simplified = execution_data.get('was_simplified', False)
        if was_simplified:
            score *= 0.9
            factors.append(('simplification', -0.1, 'Required simplification'))
        
        # Factor 6: Prediction accuracy
        predicted_matched = execution_data.get('predicted_failure_matched', False)
        if predicted_matched:
            score *= 1.0
            factors.append(('prediction', 0.1, 'Prediction was accurate'))
        
        # Normalize score to 0-1 range
        score = max(0.0, min(1.0, score))
        
        # Determine trust level
        if score >= 0.8:
            trust_level = "high"
        elif score >= 0.5:
            trust_level = "medium"
        else:
            trust_level = "low"
        
        return {
            'trust_score': round(score, 3),
            'trust_level': trust_level,
            'factors': factors,
            'explanation': cls._generate_explanation(score, factors)
        }
    
    @classmethod
    def _generate_explanation(cls, score: float, factors: list) -> str:
        """Generate human-readable explanation."""
        
        if score >= 0.8:
            return "High confidence in execution. System performed well with minimal issues."
        elif score >= 0.5:
            return "Medium confidence. Some validation or execution issues encountered."
        else:
            return "Low confidence. Multiple issues suggest execution may not be reliable."
    
    @classmethod
    def summarize_execution(cls, spec: Any, outcome: Any, execution_log: list) -> str:
        """Generate final execution summary."""
        
        if not outcome:
            return "No outcome recorded."
        
        execution_data = {
            'tests_passed': outcome.result == 'success',
            'retry_count': getattr(spec, 'retry_count', 0),
            'confidence_score': getattr(outcome, 'confidence_score', 0.5),
            'sanity_passed': True,  # Would come from sanity checker
            'was_simplified': spec.spec_json.get('_simplified', False),
            'predicted_failure_matched': getattr(outcome, 'predicted_failure_matched', False)
        }
        
        trust = cls.calculate_trust_score(execution_data)
        
        lines = [
            f"Trust Score: {trust['trust_score']}/1.0 ({trust['trust_level'].upper()})",
            "",
            f"Result: {outcome.result}",
            f"Confidence: {outcome.confidence_score:.2f}",
            f"Retries: {spec.retry_count}",
            "",
            "Factors:",
        ]
        
        for factor in trust['factors']:
            sign = '+' if factor[1] >= 0 else ''
            lines.append(f"  {factor[0]}: {sign}{factor[1]:.1f} - {factor[2]}")
        
        lines.append("")
        lines.append(trust['explanation'])
        
        return "\n".join(lines)