"""
GitHub Execution Client
=======================
Creates branches, commits generated code files, and opens Pull Requests.
Uses the GitHub REST API v3 directly (no extra libraries needed).
"""

import base64
import logging
import re
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """Thin wrapper around GitHub REST API v3."""

    BASE = "https://api.github.com"

    def __init__(self):
        self.token = getattr(settings, "GITHUB_TOKEN", "")
        self.owner = getattr(settings, "GITHUB_REPO_OWNER", "")
        self.repo = getattr(settings, "GITHUB_REPO_NAME", "")

    def enabled(self) -> bool:
        return bool(self.token and self.owner and self.repo)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> Optional[dict]:
        try:
            r = requests.get(
                f"{self.BASE}{path}",
                headers=self._headers(),
                timeout=15,
            )
            if r.ok:
                return r.json()
            logger.warning("GitHub GET %s → %s: %s", path, r.status_code, r.text[:200])
        except Exception as exc:
            logger.error("GitHub GET %s error: %s", path, exc)
        return None

    def _post(self, path: str, body: dict) -> Optional[dict]:
        try:
            r = requests.post(
                f"{self.BASE}{path}",
                json=body,
                headers=self._headers(),
                timeout=15,
            )
            if r.ok:
                return r.json()
            logger.warning("GitHub POST %s → %s: %s", path, r.status_code, r.text[:300])
        except Exception as exc:
            logger.error("GitHub POST %s error: %s", path, exc)
        return None

    def _put(self, path: str, body: dict) -> Optional[dict]:
        try:
            r = requests.put(
                f"{self.BASE}{path}",
                json=body,
                headers=self._headers(),
                timeout=15,
            )
            if r.ok:
                return r.json()
            logger.warning("GitHub PUT %s → %s: %s", path, r.status_code, r.text[:300])
        except Exception as exc:
            logger.error("GitHub PUT %s error: %s", path, exc)
        return None

    # ── helpers ────────────────────────────────────────────────────────────────

    def _repo(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"

    def get_default_branch(self) -> Optional[str]:
        """Return the repo's default branch name (usually 'main' or 'master')."""
        data = self._get(self._repo())
        return data.get("default_branch") if data else None

    def get_branch_sha(self, branch: str) -> Optional[str]:
        """Return the latest commit SHA on a branch."""
        data = self._get(f"{self._repo()}/git/ref/heads/{branch}")
        if data:
            return data.get("object", {}).get("sha")
        return None

    # ── core operations ────────────────────────────────────────────────────────

    def create_branch(self, branch_name: str, from_sha: str) -> bool:
        """Create a new branch from a given commit SHA."""
        result = self._post(
            f"{self._repo()}/git/refs",
            {"ref": f"refs/heads/{branch_name}", "sha": from_sha},
        )
        return result is not None

    def upsert_file(
        self,
        branch: str,
        file_path: str,
        content: str,
        commit_message: str,
    ) -> bool:
        """Create or update a file on a branch with a commit."""
        encoded = base64.b64encode(content.encode()).decode()

        # Check if file exists (to get its SHA for updates)
        existing = self._get(f"{self._repo()}/contents/{file_path}?ref={branch}")
        body: dict = {
            "message": commit_message,
            "content": encoded,
            "branch": branch,
        }
        if existing and isinstance(existing, dict) and "sha" in existing:
            body["sha"] = existing["sha"]

        result = self._put(f"{self._repo()}/contents/{file_path}", body)
        return result is not None

    def create_pull_request(
        self,
        branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> Optional[str]:
        """
        Open a pull request.
        Returns the PR HTML URL on success, None on failure.
        """
        result = self._post(
            f"{self._repo()}/pulls",
            {
                "title": title,
                "head": branch,
                "base": base_branch,
                "body": body,
                "draft": False,
            },
        )
        if result:
            return result.get("html_url")
        return None


def slugify_branch(name: str) -> str:
    """Convert a feature name into a valid git branch name."""
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "-", name.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return f"specflow/{slug[:60]}"


def build_pr_body(spec_json: dict, spec_id: str) -> str:
    """Build a rich PR description from spec JSON."""
    j = spec_json
    lines = [
        f"## {j.get('feature_name', 'Feature')}",
        "",
        f"**Problem:** {j.get('problem', '')}",
        "",
        f"**User Story:** {j.get('user_story', '')}",
        "",
        f"**Solution:** {j.get('solution', '')}",
        "",
        "---",
        f"*Auto-generated by SpecFlow · Spec ID: `{spec_id}`*",
    ]
    if j.get("ui_changes"):
        lines += ["", "### UI Changes"] + [f"- {c}" for c in j["ui_changes"]]
    if j.get("data_model_changes"):
        lines += ["", "### Data Model Changes"] + [f"- {c}" for c in j["data_model_changes"]]
    if j.get("workflow_changes"):
        lines += ["", "### Workflow Changes"] + [f"- {c}" for c in j["workflow_changes"]]
    return "\n".join(lines)
