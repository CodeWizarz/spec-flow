import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ProductContextEngine:
    """Stores product structure, key flows, and core entities."""
    
    _entities = {
        "user": ["signup", "login", "profile"],
        "workspace": ["create", "invite_user", "settings"],
        "project": ["create", "delete", "members"],
        "issue": ["create", "assign", "update_status", "comment"],
        "auth": ["session", "tokens", "oauth"]
    }
    
    _flows = {
        "user_signup": ["user.signup", "workspace.create", "auth.session"],
        "issue_creation": ["project.members", "issue.create"],
        "auth_flow": ["auth.oauth", "user.login", "auth.session"]
    }

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        return {
            "entities": cls._entities,
            "flows": cls._flows
        }
    
    @classmethod
    def analyze_dependencies(cls, spec_json: Dict[str, Any]) -> list:
        """Analyze what parts of the product are touched and dependencies."""
        solution = spec_json.get("solution", "").lower()
        feature_name = spec_json.get("feature_name", "").lower()
        
        deps = set()
        for entity, actions in cls._entities.items():
            if entity in solution or entity in feature_name:
                deps.add(entity)
            for action in actions:
                if action in solution or action in feature_name:
                    deps.add(entity)
                    
        return list(deps)
    
    @classmethod
    def check_consistency(cls, spec_json: Dict[str, Any]) -> bool:
        """Check if spec aligns with the product model."""
        deps = cls.analyze_dependencies(spec_json)
        
        # Example consistency check: if modifying auth, must touch user
        if "auth" in deps and "user" not in deps:
            logger.warning("Consistency Warning: Modifying auth without involving user entity.")
            return False
            
        return True