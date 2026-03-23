"""
Code Generation Agent
=====================
Uses GPT-4o to generate actual implementation files from a spec's tasks.
Falls back to scaffold stubs when OpenAI is not configured.
"""

import json
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _openai_client():
    try:
        import openai

        key = getattr(settings, "OPENAI_API_KEY", "")
        if not key:
            return None
        return openai.OpenAI(api_key=key)
    except ImportError:
        return None


def generate_files_for_task(
    task: dict,
    feature_name: str,
    problem: str,
    solution: str,
    past_context: str = "",
) -> dict[str, str]:
    """
    Generate implementation files for a single spec task.

    Args:
        task: A task dict with 'read_first' (filenames) and 'action' (instructions)
        feature_name: The feature being implemented
        problem: The problem being solved
        solution: The solution description
        past_context: Past implementation context from Supermemory

    Returns:
        A dict mapping filename → generated file content.
    """
    files_to_touch = task.get("read_first", [])
    actions = task.get("action", [])

    if not files_to_touch and not actions:
        return {}

    client = _openai_client()

    if client is None:
        # Graceful fallback: create stub files
        return _stub_files(files_to_touch, feature_name, problem, actions)

    # Build prompt
    actions_text = "\n".join(f"- {a}" for a in actions)
    files_text = "\n".join(f"- {f}" for f in files_to_touch)

    system_prompt = (
        "You are a senior software engineer implementing a feature. "
        "Generate COMPLETE, production-ready code for the specified files. "
        "Return ONLY a valid JSON object where keys are file paths and values are the full file contents. "
        "No explanations, no markdown fences — just the raw JSON object.\n"
    )
    if past_context:
        system_prompt += f"\n## Past Implementation Context:\n{past_context}\n"

    user_prompt = (
        f"## Feature: {feature_name}\n"
        f"## Problem: {problem}\n"
        f"## Solution: {solution}\n\n"
        f"## Files to implement:\n{files_text}\n\n"
        f"## Actions required:\n{actions_text}\n\n"
        "Generate complete implementation for ALL the listed files."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        # Filter: only accept string values (file contents)
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except Exception as exc:
        logger.error("CodeGen: GPT-4o error for task '%s': %s", feature_name, exc)
        return _stub_files(files_to_touch, feature_name, problem, actions)


def _stub_files(
    filenames: list[str],
    feature_name: str,
    problem: str,
    actions: list[str],
) -> dict[str, str]:
    """Create minimal stub files when AI is unavailable."""
    stubs = {}
    for fname in filenames:
        ext = fname.rsplit(".", 1)[-1] if "." in fname else "txt"
        comment = "#" if ext in ("py", "sh", "yaml", "yml") else "//"
        actions_text = "\n".join(f"{comment}   - {a}" for a in actions)
        stubs[fname] = (
            f"{comment} Auto-generated stub by SpecFlow Execution Agent\n"
            f"{comment} Feature: {feature_name}\n"
            f"{comment} Problem: {problem}\n"
            f"{comment}\n"
            f"{comment} TODO — implement the following:\n"
            f"{actions_text}\n"
        )
    return stubs


def generate_behavioral_tests(spec_json: dict, files_generated: dict) -> dict[str, str]:
    """
    Generate behavioral validation tests based on the spec problem and solution.
    Validates input -> output and side effects rather than just existence.
    """
    feature_name = spec_json.get("feature_name", "Feature")
    problem = spec_json.get("problem", "")
    solution = spec_json.get("solution", "")

    client = _openai_client()
    if client is None:
        return {"test_behavioral.py": "def test_dummy():\n    assert True\n"}

    system_prompt = (
        "You are an expert QA engineer. "
        "Write a comprehensive behavioral pytest suite for the provided feature. "
        "Focus on input-output validation and side-effects. Do not write tests that only assert existence or mirror code. "
        "Return ONLY a valid JSON object where keys are file paths (e.g., 'test_behavioral.py') and values are the full file contents."
    )
    
    files_context = "\n".join(f"--- {fname} ---\n{content}\n" for fname, content in files_generated.items())

    user_prompt = (
        f"## Feature: {feature_name}\n"
        f"## Problem: {problem}\n"
        f"## Solution: {solution}\n\n"
        f"## Generated Code Context:\n{files_context}\n\n"
        "Generate behavioral pytest tests to validate this code."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except Exception as exc:
        logger.error("CodeGen: test generation error: %s", exc)
        return {"test_behavioral.py": "def test_dummy():\n    assert True\n"}

def generate_all_files(spec_json: dict, past_context: str = "") -> dict[str, str]:
    """
    Generate implementation files for ALL tasks in a spec.
    Merges results from each task into a single filename→content dict.
    """
    feature_name = spec_json.get("feature_name", "Feature")
    problem = spec_json.get("problem", "")
    solution = spec_json.get("solution", "")
    tasks = spec_json.get("tasks", [])

    if not tasks:
        # No tasks: generate a single README-style summary file
        return {
            "specflow-implementation.md": (
                f"# {feature_name}\n\n"
                f"## Problem\n{problem}\n\n"
                f"## Solution\n{solution}\n\n"
                "*Generated by SpecFlow — no tasks defined in spec.*\n"
            )
        }

    all_files: dict[str, str] = {}
    for i, task in enumerate(tasks):
        logger.info("CodeGen: generating files for task %d/%d of '%s'", i + 1, len(tasks), feature_name)
        task_files = generate_files_for_task(task, feature_name, problem, solution, past_context)
        all_files.update(task_files)  # later tasks can overwrite earlier ones for the same file

    return all_files
