# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.signals.models import GeneratedSpec, Insight, Outcome, ProductMemory, Signal, SpecIssue


class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = [
            "id",
            "workspace",
            "title",
            "content",
            "file",
            "source",
            "processing_status",
            "source_metadata",
            "supermemory_doc_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "supermemory_doc_id",
            "created_at",
            "updated_at",
        ]


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insight
        fields = [
            "id",
            "workspace",
            "theme",
            "problem",
            "root_cause",
            "evidence",
            "frequency",
            "supermemory_doc_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "supermemory_doc_id",
            "created_at",
            "updated_at",
        ]


class SpecIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecIssue
        fields = [
            "id",
            "workspace",
            "spec",
            "title",
            "description",
            "status",
            "assignee_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "spec",
            "created_at",
            "updated_at",
        ]


class ProductMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMemory
        fields = [
            "id",
            "workspace",
            "category",
            "title",
            "summary",
            "metadata",
            "spec",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "created_at",
            "updated_at",
        ]


class OutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outcome
        fields = [
            "id",
            "workspace",
            "spec",
            "result",
            "success_score",
            "metrics_before",
            "metrics_after",
            "notes",
            "pr_url",
            "supermemory_doc_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace", "supermemory_doc_id", "created_at", "updated_at"]


class GeneratedSpecSerializer(serializers.ModelSerializer):
    issues = SpecIssueSerializer(many=True, read_only=True)
    outcome = OutcomeSerializer(read_only=True)

    class Meta:
        model = GeneratedSpec
        fields = [
            "id",
            "workspace",
            "title",
            "spec_json",
            "agent_payload",
            "status",
            # Prioritization Engine scores
            "impact_score",
            "effort_score",
            "priority_score",
            # Advanced Prioritization Engine v2
            "confidence_score",
            "recency_weight",
            "risk_score",
            # Supermemory reference
            "supermemory_doc_id",
            # Execution tracking
            "execution_status",
            "github_pr_url",
            "github_branch",
            "execution_log",
            # Nested (read-only)
            "issues",
            "outcome",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "agent_payload",
            # priority_score is auto-computed by the Prioritization Agent
            "priority_score",
            # Advanced scores are auto-computed
            "confidence_score",
            "recency_weight",
            "risk_score",
            "supermemory_doc_id",
            # Execution tracking is managed server-side
            "execution_log",
            "github_pr_url",
            "github_branch",
            "created_at",
            "updated_at",
        ]
