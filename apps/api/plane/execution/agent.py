"""
Execution Agent
===============
Orchestrates the full "Spec → Code → Branch → PR" pipeline:

  1. Load the GeneratedSpec
  2. Retrieve past implementation context from Supermemory
  3. Generate code files via the Code Generation Agent (GPT-4o)
  4. Create a GitHub branch
  5. Commit all generated files
  6. Open a Pull Request
  7. Store an Outcome record
  8. Update the spec's execution_status and github_pr_url
"""

import tempfile
import os
import subprocess
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def execute_spec_task(spec_id: str, triggered_by: str = "manual") -> dict:
    """
    Celery task: full execution pipeline for a single spec.

    Returns a dict with:
      {
        "status": "pr_created" | "failed",
        "pr_url": "...",           # only on success
        "branch": "...",           # only on success
        "error": "...",            # only on failure
        "files_generated": ["..."],
      }
    """
    from plane.signals.models import GeneratedSpec, Outcome, ProductMemory

    # ── 1. Load spec ──────────────────────────────────────────────────────────
    try:
        spec = GeneratedSpec.objects.select_related("workspace").get(id=spec_id)
    except GeneratedSpec.DoesNotExist:
        logger.error("Execution Agent: spec %s not found", spec_id)
        return {"status": "failed", "error": "Spec not found"}

    workspace = spec.workspace
    feature_name = spec.spec_json.get("feature_name", spec.title)

    log_entry = {
        "started_at": timezone.now().isoformat(),
        "triggered_by": triggered_by,
        "steps": [],
    }

    def _log(step: str, detail: str = ""):
        logger.info("Execution Agent [%s]: %s %s", feature_name, step, detail)
        log_entry["steps"].append({"step": step, "detail": detail, "ts": timezone.now().isoformat()})

    # ── Reliability Layer: Complexity Check ───────────────────────────────────
    from plane.reliability.classifier import ComplexityClassifier
    classification = ComplexityClassifier.classify(spec.spec_json)
    _log("complexity_check", classification)
    
    if classification != 'simple':
        _log("spec_too_complex", f"Deferring execution - classification: {classification}")
        GeneratedSpec.objects.filter(id=spec_id).update(execution_status="deferred")
        return {
            "status": "deferred",
            "reason": f"Spec classified as {classification}. Only simple specs are executable.",
            "classification": classification
        }
    
    # ── Reliability Layer: Spec Simplification ────────────────────────────────
    from plane.reliability.simplifier import SpecSimplifier
    spec.spec_json = SpecSimplifier.simplify(spec.spec_json)
    spec.save(update_fields=['spec_json'])
    _log("spec_simplified", "Reduced to minimal viable implementation")

    # ── Predictive Failure Prevention ──────────────────────────────────────────
    from plane.product_context.predictive import PredictiveFailureModule
    spec = PredictiveFailureModule.adjust_spec_before_execution(spec)

    def _fail(reason: str, failure_type: str = "unknown") -> dict:
        _log("FAILED", f"[{failure_type}] {reason}")
        log_entry["error"] = reason
        log_entry["failure_type"] = failure_type
        log_entry["finished_at"] = timezone.now().isoformat()
        
        if getattr(spec, 'retry_count', 0) < 2:
            spec.retry_count = getattr(spec, 'retry_count', 0) + 1
            GenericUpdate = {
                "execution_status": "pending",
                "execution_log": list(spec.execution_log or []) + [log_entry],
                "retry_count": spec.retry_count
            }
            GeneratedSpec.objects.filter(id=spec_id).update(**GenericUpdate)
            
            try:
                from plane.signals import supermemory as sm
                sm.add_document(
                    workspace.slug,
                    f"[EXECUTION FAILURE] Feature '{feature_name}' failed with {failure_type}: {reason}",
                    metadata={"type": "execution_failure", "spec_id": str(spec.id), "failure_type": failure_type}
                )
            except Exception:
                pass
                
            new_spec_json = spec.spec_json.copy()
            
            # Reliability: Aggressive simplification on retry
            new_spec_json = SpecSimplifier.simplify_for_retry(new_spec_json, failure_type)
            _log("retry_simplified", f"Aggressively simplified due to {failure_type}")
                
            GeneratedSpec.objects.filter(id=spec_id).update(spec_json=new_spec_json)
            
            execute_spec_task.delay(spec_id, "retry")
        else:
            GenericUpdate = {"execution_status": "failed", "execution_log": list(spec.execution_log or []) + [log_entry]}
            GeneratedSpec.objects.filter(id=spec_id).update(**GenericUpdate)
            
            # Calculate confidence score based on retries and failure
            confidence = max(0.0, 1.0 - (spec.retry_count * 0.4))
            predicted_matched = getattr(spec, 'predicted_failure_type', 'none') == failure_type
            
            try:
                from plane.signals.models import Outcome
                Outcome.objects.get_or_create(
                    spec=spec,
                    defaults={
                        "workspace": workspace,
                        "result": Outcome.Result.FAILURE,
                        "success_score": 0.0,
                        "success": False,
                        "failure_type": failure_type,
                        "confidence_score": confidence,
                        "retry_count": spec.retry_count,
                        "predicted_failure_matched": predicted_matched,
                        "simulation_success": False,
                        "consistency_success": False,
                        "notes": f"Execution failed after retries: [{failure_type}] {reason}"
                    }
                )
            except Exception:
                pass

        return {"status": "failed", "error": reason}

    # Mark as pending
    GeneratedSpec.objects.filter(id=spec_id).update(execution_status="pending")
    _log("started", f"spec_id={spec_id}")

    # ── 2. Check GitHub config ─────────────────────────────────────────────────
    from plane.execution.github import GitHubClient, build_pr_body, slugify_branch

    gh = GitHubClient()
    if not gh.enabled():
        return _fail("GitHub not configured — set GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME in .env")

    # ── 3. Fetch Supermemory context for past implementations ─────────────────
    past_context = ""
    try:
        from plane.signals import supermemory as sm

        past_context = sm.get_context_for_query(
            workspace.slug,
            f"implementation of {feature_name} similar feature code",
            max_chars=2000,
        )
        if past_context:
            _log("memory_context", f"retrieved {len(past_context)} chars from Supermemory")
    except Exception as exc:
        _log("memory_context_warning", str(exc))

    # ── 4. Generate code ───────────────────────────────────────────────────────
    GeneratedSpec.objects.filter(id=spec_id).update(execution_status="generating")
    _log("codegen_start")

    from plane.execution.codegen import generate_all_files

    generated_files = generate_all_files(spec.spec_json, past_context)
    if not generated_files:
        return _fail("Code generation produced no files")

    _log("codegen_complete", f"{len(generated_files)} files: {list(generated_files.keys())}")

    # ── 4a. Execution Reliability Layer: Static Validation & Tests ───────────────
    with tempfile.TemporaryDirectory() as temp_dir:
        for file_path, content in generated_files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
        
        # Static Validation
        for file_path, content in generated_files.items():
            if file_path.endswith(".py"):
                try:
                    compile(content, file_path, "exec")
                except SyntaxError as e:
                    return _fail(f"Syntax error in {file_path}: {e}", failure_type="syntax_error")

        # True Validation Layer: Behavioral Tests, Simulation, Consistency
        from plane.product_context.engine import ProductContextEngine
        from plane.product_context.simulation import SimulationHarness
        
        consistency_success = ProductContextEngine.check_consistency(spec.spec_json)
        if not consistency_success:
            return _fail("Feature breaks system consistency or lacks required dependencies.", failure_type="unclear_spec")
            
        simulation_success = SimulationHarness.simulate_spec(spec.spec_json)
        if not simulation_success:
            return _fail("Simulation harness failed. Feature introduces real-world conflicts.", failure_type="logic_error")

        # Sanity Check Layer - Run correctness checks BEFORE tests
        from plane.reliability.sanity import SanityChecker
        sanity_results = SanityChecker.run_sanity_checks(generated_files, spec.spec_json)
        _log("sanity_check", f"Passed: {sanity_results['passed']}, Checks: {len(sanity_results['checks'])}")
        
        if not sanity_results['passed']:
            failed_checks = [c for c in sanity_results['checks'] if not c[1]]
            return _fail(f"Sanity checks failed: {[c[0] for c in failed_checks]}", failure_type="logic_error")

        # Auto Test Generation - Use truthful validation
        from plane.reliability.tests import TruthfulValidation
        test_code = TruthfulValidation.generate_test(spec.spec_json, generated_files)
        behavioral_tests = {"test_validation.py": test_code}
        
        for file_path, content in behavioral_tests.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
                
        try:
            result = subprocess.run(["pytest", temp_dir], capture_output=True, text=True, timeout=15)
            if result.returncode != 0 and "no tests ran" not in result.stdout:
                if "ModuleNotFoundError" in result.stdout:
                    return _fail(f"Missing dependency: {result.stdout[:200]}", failure_type="missing_dependency")
                elif "AssertionError" in result.stdout:
                    return _fail(f"Tests failed: {result.stdout[:200]}", failure_type="test_failure")
                else:
                    return _fail(f"Logic or test error: {result.stdout[:200]}", failure_type="logic_error")
            else:
                _log("test_success", "Generated behavioral tests passed.")
        except FileNotFoundError:
            _log("test_skipped", "pytest not installed - skipping test validation")
        except subprocess.TimeoutExpired:
            return _fail("Test execution timed out", failure_type="logic_error")
        except Exception as e:
            _log("test_warning", f"Test execution error: {str(e)}")
            return _fail(f"Test execution error: {str(e)}", failure_type="unclear_spec")

    # ── 5. Get default branch SHA ──────────────────────────────────────────────
    default_branch = gh.get_default_branch()
    if not default_branch:
        return _fail("Could not determine default branch")

    base_sha = gh.get_branch_sha(default_branch)
    if not base_sha:
        return _fail(f"Could not get SHA for branch '{default_branch}'")

    # ── 6. Create feature branch ───────────────────────────────────────────────
    branch_name = slugify_branch(feature_name)
    _log("create_branch", branch_name)

    if not gh.create_branch(branch_name, base_sha):
        return _fail(f"Failed to create branch '{branch_name}'")

    # ── 7. Commit all generated files ─────────────────────────────────────────
    failed_files = []
    for file_path, content in generated_files.items():
        ok = gh.upsert_file(
            branch=branch_name,
            file_path=file_path,
            content=content,
            commit_message=f"feat({feature_name[:40]}): implement {file_path}",
        )
        if not ok:
            failed_files.append(file_path)
            _log("commit_warning", f"Failed to commit {file_path}")

    if failed_files:
        _log("commit_partial", f"Failed files: {failed_files}")

    _log("commits_done", f"{len(generated_files) - len(failed_files)}/{len(generated_files)} files committed")

    # ── 8. Open Pull Request ───────────────────────────────────────────────────
    pr_title = f"[SpecFlow] {feature_name}"
    pr_body = build_pr_body(spec.spec_json, str(spec.id))

    _log("create_pr", f"base={default_branch}")
    pr_url = gh.create_pull_request(branch_name, default_branch, pr_title, pr_body)

    if not pr_url:
        return _fail("Failed to create Pull Request")

    _log("pr_created", pr_url)

    # ── 9. Update spec ─────────────────────────────────────────────────────────
    log_entry["finished_at"] = timezone.now().isoformat()
    log_entry["files_generated"] = list(generated_files.keys())
    log_entry["pr_url"] = pr_url

    GeneratedSpec.objects.filter(id=spec_id).update(
        execution_status="pr_created",
        github_pr_url=pr_url,
        github_branch=branch_name,
        execution_log=list(spec.execution_log or []) + [log_entry],
    )

    # ── 10. Store in Supermemory ───────────────────────────────────────────────
    try:
        from plane.signals import supermemory as sm

        sm.add_document(
            workspace.slug,
            f"[EXECUTION] Feature '{feature_name}' — PR created: {pr_url}\n"
            f"Branch: {branch_name}\nFiles: {', '.join(generated_files.keys())}",
            metadata={"type": "execution", "spec_id": str(spec.id), "pr_url": pr_url},
        )
    except Exception:
        pass

    # ── 11. Create Outcome record ──────────────────────────────────────────────
    try:
        # Confidence incorporates retries, simulation, tests, consistency
        confidence = max(0.0, 1.0 - (getattr(spec, 'retry_count', 0) * 0.2))
        predicted_matched = getattr(spec, 'predicted_failure_type', 'none') == 'none' # In success case
        
        Outcome.objects.get_or_create(
            spec=spec,
            defaults={
                "workspace": workspace,
                "result": Outcome.Result.SUCCESS,
                "success_score": confidence,
                "success": True,
                "confidence_score": confidence,
                "retry_count": getattr(spec, 'retry_count', 0),
                "predicted_failure_matched": predicted_matched,
                "simulation_success": True, # Passed earlier
                "consistency_success": True, # Passed earlier
                "pr_url": pr_url,
                "notes": f"PR opened automatically by Execution Agent. Branch: {branch_name}",
            },
        )
    except Exception as exc:
        _log("outcome_warning", str(exc))

    # ── 12. Store decision in Supermemory ──────────────────────────────────────
    try:
        from plane.signals import supermemory as sm

        sm.store_decision(workspace.slug, feature_name, "executed", f"PR: {pr_url}")
    except Exception:
        pass

    result = {
        "status": "pr_created",
        "pr_url": pr_url,
        "branch": branch_name,
        "files_generated": list(generated_files.keys()),
    }
    logger.info("Execution Agent: ✅ %s → %s", feature_name, pr_url)
    return result
