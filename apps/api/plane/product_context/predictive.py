import logging
from typing import Dict, Any
from plane.signals.models import GeneratedSpec, ProductMemory

logger = logging.getLogger(__name__)

class PredictiveFailureModule:
    
    @classmethod
    def predict_failure(cls, spec: GeneratedSpec) -> str:
        """Predict likely failure type based on memory and spec content."""
        from plane.product_context.engine import ProductContextEngine
        
        deps = ProductContextEngine.analyze_dependencies(spec.spec_json)
        
        # Query recent memory for failures related to these dependencies
        from django.db.models import Q
        query = Q(category=ProductMemory.Category.SPEC_REFERENCE)
        
        memory_keywords = deps + [spec.title.split()[0]] if deps else [spec.title.split()[0]]
        for kw in memory_keywords:
            query |= Q(title__icontains=kw) | Q(summary__icontains=kw)
            
        memories = ProductMemory.objects.filter(workspace=spec.workspace, success_weight__lt=1.0).filter(query).order_by("-created_at")[:5]
        
        if memories.exists():
            # Try to guess failure type from summaries
            for m in memories:
                if "syntax_error" in m.summary:
                    return "syntax_error"
                if "test_failure" in m.summary:
                    return "test_failure"
                if "missing_dependency" in m.summary:
                    return "missing_dependency"
                if "logic_error" in m.summary:
                    return "logic_error"
                if "unclear_spec" in m.summary:
                    return "unclear_spec"
                    
        # Basic predictive heuristics based on product context
        if "auth" in deps:
            return "missing_dependency" # Auth features often fail due to missing context
        elif "ui_changes" in spec.spec_json and len(spec.spec_json["ui_changes"]) > 0:
            return "syntax_error" 
            
        return "none"
        
    @classmethod
    def adjust_spec_before_execution(cls, spec: GeneratedSpec) -> GeneratedSpec:
        """Adjust spec to prevent predictive failure."""
        predicted_failure = cls.predict_failure(spec)
        spec.predicted_failure_type = predicted_failure
        spec.save(update_fields=["predicted_failure_type"])
        
        if predicted_failure != "none":
            spec_json = spec.spec_json.copy()
            prevention_prompt = f"\n(PREDICTIVE WARNING: This spec is likely to fail with {predicted_failure}. Please defensively guard against this.)"
            spec_json["problem"] = spec_json.get("problem", "") + prevention_prompt
            spec.spec_json = spec_json
            spec.save(update_fields=["spec_json"])
            logger.info(f"Predictive Failure Module: Adjusted spec {spec.id} to prevent {predicted_failure}")
            
        return spec