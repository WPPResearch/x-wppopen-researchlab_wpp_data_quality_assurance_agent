# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test that JSON statistical reports are uploaded to GCS with session-based paths.

Run with:
    pytest tests/test_gcs_json_report.py -v -s

Requires:
    - ARTIFACT_BUCKET_NAME set in .env (or environment)
    - GCS credentials (application-default or service account)
"""

import json
import os
import sys
import uuid

import pytest

# Load env vars BEFORE importing data_science modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("BQ_DATASET_ID", "dummy")
os.environ.setdefault("BQ_DATA_PROJECT_ID", "dummy")

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

from data_science.sub_agents.report.tools import save_json_statistical_report  # noqa: E402


def _make_mock_tool_context(session_id: str) -> MagicMock:
    """Create a mock tool_context with a given session_id and a working save_artifact."""
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.id = session_id
    ctx.save_artifact = AsyncMock(return_value=0)
    return ctx


def _make_sample_json(table_name: str = "test_dataset.test_table") -> str:
    """Create a minimal JSON report payload."""
    return json.dumps(
        {
            "report_metadata": {
                "table_name": table_name,
                "generated_at": "2026-02-19T15:00:00Z",
            },
            "schema_summary": {
                "total_rows": 100,
                "number_of_columns": 3,
                "column_names": ["col_a", "col_b", "col_c"],
            },
            "numerical_columns": [],
            "categorical_columns": [],
        },
    )


BUCKET_NAME = os.environ.get("ARTIFACT_BUCKET_NAME")


@pytest.mark.skipif(not BUCKET_NAME, reason="ARTIFACT_BUCKET_NAME not set")
class TestGcsJsonReportUpload:
    """Integration tests that actually upload to GCS and verify the blob exists."""

    @pytest.fixture(autouse=True)
    def _setup_gcs(self):
        """Set up GCS client and track blobs to clean up after tests."""
        from google.cloud import storage

        self.gcs_client = storage.Client()
        self.bucket = self.gcs_client.bucket(BUCKET_NAME)
        self._blobs_to_cleanup = []
        yield
        # Cleanup: delete test blobs after each test
        for blob_path in self._blobs_to_cleanup:
            blob = self.bucket.blob(blob_path)
            if blob.exists():
                blob.delete()

    @pytest.mark.asyncio
    async def test_report_uploaded_with_session_id_in_path(self):
        """Verify the JSON report lands under json_reports/{session_id}/{filename}."""
        session_id = str(uuid.uuid4())
        table_name = "test_project.test_dataset.test_upload_table"
        expected_filename = "test_project_test_dataset_test_upload_table.json"
        expected_blob_path = f"json_reports/{session_id}/{expected_filename}"

        ctx = _make_mock_tool_context(session_id)
        content = _make_sample_json(table_name)

        result = await save_json_statistical_report(
            content_to_save=content,
            tool_context=ctx,
        )

        # Track for cleanup
        self._blobs_to_cleanup.append(expected_blob_path)

        # Assertions
        assert result["status"] == "success", f"Unexpected result: {result}"
        assert "gcs_uri" in result, f"No gcs_uri in result: {result}"
        assert (
            session_id in result["gcs_uri"]
        ), f"Session ID not in GCS URI: {result['gcs_uri']}"

        # Verify the blob actually exists in GCS
        blob = self.bucket.blob(expected_blob_path)
        assert blob.exists(), f"Blob not found at {expected_blob_path}"

        # Verify content is correct
        downloaded = blob.download_as_text()
        parsed = json.loads(downloaded)
        assert parsed["report_metadata"]["table_name"] == table_name

    @pytest.mark.asyncio
    async def test_different_sessions_do_not_overwrite(self):
        """Two sessions analyzing the same table should produce two separate blobs."""
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())
        table_name = "test_project.test_dataset.same_table"
        expected_filename = "test_project_test_dataset_same_table.json"

        blob_path_1 = f"json_reports/{session_id_1}/{expected_filename}"
        blob_path_2 = f"json_reports/{session_id_2}/{expected_filename}"

        # Session 1
        ctx1 = _make_mock_tool_context(session_id_1)
        content1 = _make_sample_json(table_name)
        result1 = await save_json_statistical_report(
            content_to_save=content1,
            tool_context=ctx1,
        )
        self._blobs_to_cleanup.append(blob_path_1)

        # Session 2
        ctx2 = _make_mock_tool_context(session_id_2)
        content2 = _make_sample_json(table_name)
        result2 = await save_json_statistical_report(
            content_to_save=content2,
            tool_context=ctx2,
        )
        self._blobs_to_cleanup.append(blob_path_2)

        # Both should succeed
        assert result1["status"] == "success"
        assert result2["status"] == "success"

        # Both blobs should exist independently
        assert self.bucket.blob(blob_path_1).exists(), f"Blob 1 missing: {blob_path_1}"
        assert self.bucket.blob(blob_path_2).exists(), f"Blob 2 missing: {blob_path_2}"

        # URIs should differ
        assert result1["gcs_uri"] != result2["gcs_uri"]
