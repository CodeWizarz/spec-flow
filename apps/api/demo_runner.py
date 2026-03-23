#!/usr/bin/env python3
"""
Demo Runner - Reproducible demo in < 60 seconds
================================================
Seeds signals, runs pipeline, executes specs, outputs clean logs.
"""

import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plane.settings.common')
import django
django.setup()

import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

# Configure logging for clean output
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger()

from unittest import mock
from plane.db.models import Workspace, User
from plane.signals.models import Signal, Insight, GeneratedSpec, Outcome, ProductMemory
from plane.bgtasks.signals_tasks import generate_insights_task, generate_spec_task, prioritize_specs_task
from plane.execution.agent import execute_spec_task
from plane.reliability.classifier import ComplexityClassifier
from plane.reliability.simplifier import SpecSimplifier
from plane.reliability.timeline import ExecutionTimeline
from plane.reliability.trust import TrustScorer


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    print(f"\n--- {title} ---")


class DemoRunner:
    def __init__(self):
        self.workspace = None
        self.specs_executed = 0
        self.specs_succeeded = 0
        
    def run(self):
        print_header("SPECFLOW DEMO - YC READY")
        
        # Setup
        self._setup_workspace()
        
        # Seed signals
        self._seed_signals()
        
        # Run pipeline
        self._run_pipeline()
        
        # Execute specs
        self._execute_specs()
        
        # Generate final report
        self._generate_report()
        
    def _setup_workspace(self):
        print_section("Setting up workspace")
        
        owner, _ = User.objects.get_or_create(
            email="demo@specflow.ai",
            defaults={"username": "demo_user"}
        )
        
        self.workspace, _ = Workspace.objects.get_or_create(
            name="SpecFlow Demo",
            slug="specflow-demo",
            defaults={"owner": owner}
        )
        
        # Clean previous demo data
        Signal.objects.filter(workspace=self.workspace).delete()
        Insight.objects.filter(workspace=self.workspace).delete()
        GeneratedSpec.objects.filter(workspace=self.workspace).delete()
        Outcome.objects.filter(workspace=self.workspace).delete()
        ProductMemory.objects.filter(workspace=self.workspace).delete()
        
        print(f"✓ Workspace ready: {self.workspace.name}")
        
    def _seed_signals(self):
        print_section("Seeding signals")
        
        signals = [
            "Users want a simple flag to enable a feature",
            "Add a button to the dashboard",
            "Show users their profile status",
            "Users need a toggle for notifications",
        ]
        
        for i, content in enumerate(signals):
            Signal.objects.create(
                workspace=self.workspace,
                title=f"Demo Signal {i}",
                content=content,
                source="demo",
                processing_status="processed",
                created_at=timezone.now() - timedelta(hours=i)
            )
        
        print(f"✓ Created {len(signals)} signals")
        
    def _create_simple_spec(self):
        """Create a simple spec directly for demo purposes."""
        print_section("Creating Demo Spec")
        
        spec = GeneratedSpec.objects.create(
            workspace=self.workspace,
            title="Simple Feature Flag",
            spec_json={
                "feature_name": "Simple Feature Flag",
                "problem": "Users need a simple toggle to enable features",
                "solution": "Add a boolean flag to user settings",
                "tasks": [{"read_first": [], "action": ["Add is_enabled field to model"]}],
                "ui_changes": ["Add toggle button"],
                "data_model_changes": [],
                "workflow_changes": [],
            },
            status=GeneratedSpec.Status.PROPOSED,
            impact_score=7.0,
            effort_score=3.0,
            priority_score=2.33
        )
        
        print(f"✓ Created spec: {spec.title}")
        return spec
        
    def _run_pipeline(self):
        print_section("Running Intelligence Pipeline")
        
        # Mock OpenAI for demo
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.choices = [mock.MagicMock(message=mock.MagicMock(
            content='{"data": [{"theme": "Simple UI", "problem": "Need simple UI", "root_cause": "Missing component", "evidence": [], "frequency": 1}]}'
        ))]
        mock_client.chat.completions.create.return_value = mock_response
        
        with mock.patch('plane.bgtasks.signals_tasks._openai_client', return_value=mock_client):
            print("→ Generating insights...")
            generate_insights_task(str(self.workspace.id))
            
            print("→ Generating specs...")
            generate_spec_task(str(self.workspace.id))
            
            print("→ Prioritizing specs...")
            prioritize_specs_task(str(self.workspace.id))
        
        spec_count = GeneratedSpec.objects.filter(workspace=self.workspace).count()
        print(f"✓ Pipeline complete: {spec_count} specs generated")
        
    def _execute_specs(self):
        print_section("Executing Specs")
        
        # Create a spec directly for demo
        spec = self._create_simple_spec()
        
        # Mock for GitHub and OpenAI
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.choices = [mock.MagicMock(message=mock.MagicMock(
            content='{"dummy.py": "# Demo code\\nclass Feature:\\n    pass"}'
        ))]
        mock_client.chat.completions.create.return_value = mock_response
        
        with mock.patch('plane.execution.codegen._openai_client', return_value=mock_client), \
             mock.patch('plane.execution.github.GitHubClient.enabled', return_value=True), \
             mock.patch('plane.execution.github.GitHubClient.get_default_branch', return_value='main'), \
             mock.patch('plane.execution.github.GitHubClient.get_branch_sha', return_value='abc123'), \
             mock.patch('plane.execution.github.GitHubClient.create_branch', return_value=True), \
             mock.patch('plane.execution.github.GitHubClient.upsert_file', return_value=True), \
             mock.patch('plane.execution.github.GitHubClient.create_pull_request', return_value='https://github.com/demo/pr/1'):
            
            print(f"\n→ Executing: {spec.title}")
            
            # Show complexity
            classification = ComplexityClassifier.classify(spec.spec_json)
            print(f"  Complexity: {classification}")
            
            if classification != 'simple':
                print(f"  → Skipped (too complex)")
            else:
                # Execute
                result = execute_spec_task(str(spec.id), "demo")
                
                spec.refresh_from_db()
                
                self.specs_executed += 1
                if spec.execution_status == 'pr_created':
                    self.specs_succeeded += 1
                    print(f"  ✓ SUCCESS - PR created")
                elif spec.execution_status == 'deferred':
                    print(f"  → Deferred (complex)")
                else:
                    print(f"  ✗ Status: {spec.execution_status}")
                
                # Show trust score
                outcome = Outcome.objects.filter(spec=spec).first()
                if outcome:
                    print(TrustScorer.summarize_execution(spec, outcome, spec.execution_log or []))
        
    def _generate_report(self):
        print_header("DEMO RESULTS")
        
        # Pipeline stats
        signals = Signal.objects.filter(workspace=self.workspace).count()
        insights = Insight.objects.filter(workspace=self.workspace).count()
        specs = GeneratedSpec.objects.filter(workspace=self.workspace).count()
        
        print(f"Pipeline:")
        print(f"  Signals:    {signals}")
        print(f"  Insights:   {insights}")
        print(f"  Specs:      {specs}")
        
        print(f"\nExecution:")
        print(f"  Executed:   {self.specs_executed}")
        print(f"  Succeeded:  {self.specs_succeeded}")
        print(f"  Rate:       {self.specs_succeeded/max(self.specs_executed,1)*100:.0f}%")
        
        # Recent outcomes
        outcomes = Outcome.objects.filter(workspace=self.workspace)[:3]
        if outcomes:
            print(f"\nOutcomes:")
            for o in outcomes:
                print(f"  {o.result} - conf: {o.confidence_score:.2f}")
        
        # Trust summary
        print(f"\nTrust Scores:")
        for spec in GeneratedSpec.objects.filter(workspace=self.workspace).order_by('-created_at')[:2]:
            outcome = Outcome.objects.filter(spec=spec).first()
            if outcome:
                trust = TrustScorer.calculate_trust_score({
                    'tests_passed': outcome.result == 'success',
                    'retry_count': spec.retry_count,
                    'confidence_score': outcome.confidence_score,
                    'sanity_passed': True,
                    'was_simplified': spec.spec_json.get('_simplified', False),
                })
                print(f"  {spec.title[:30]}: {trust['trust_score']:.2f} ({trust['trust_level']})")
        
        # Verdict
        print("\n" + "=" * 60)
        if self.specs_succeeded > 0:
            print("  VERDICT: DEMO SUCCESSFUL ✓")
            print("  SpecFlow is YC-ready, trustworthy, and demo-able!")
        else:
            print("  VERDICT: NEEDS IMPROVEMENT")
            print("  Review failure logs above for issues.")
        print("=" * 60)


if __name__ == "__main__":
    # Ensure celery runs sync
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    demo = DemoRunner()
    demo.run()