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

"""Comparison tools"""

from typing import Dict, Any
from google.adk.tools import ToolContext


def compare_table_columns(
    table_id_1: str,
    table_id_2: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Compares the number of columns and their names using the pre-loaded session schema.

    This tool is fast because it uses the context loaded during setup instead of making an API call.
    """
    # Retrieve the schema dictionary populated by setup_before_agent_call
    schema_info = (
        tool_context.state.get("database_settings", {})
        .get("bigquery", {})
        .get("schema", {})
    )

    def get_cols(tid):
        # Exact match or find table name in keys (e.g. 'marketing_data' in 'project.dataset.marketing_data')
        if tid in schema_info:
            return [field[0] for field in schema_info[tid]["table_schema"]]
        for key in schema_info:
            if tid == key.split(".")[-1] or tid == key:
                return [field[0] for field in schema_info[key]["table_schema"]]
        return None

    cols1 = get_cols(tid=table_id_1)
    cols2 = get_cols(tid=table_id_2)

    if cols1 is None or cols2 is None:
        return {
            "error": "Table(s) not found in schema cache.",
            "available_tables": list(schema_info.keys()),
        }

    set1, set2 = set(cols1), set(cols2)

    return {
        "match": set1 == set2,
        "table_1": {"name": table_id_1, "count": len(cols1)},
        "table_2": {"name": table_id_2, "count": len(cols2)},
        "differences": {"only_in_1": list(set1 - set2), "only_in_2": list(set2 - set1)},
    }


def get_volume_metrics(
    table_id_1: str,
    table_id_2: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Compares the row counts of two tables using the pre-loaded session schema.

    This tool is fast because it uses the cached row counts loaded during setup.
    """
    schema_info = (
        tool_context.state.get("database_settings", {})
        .get("bigquery", {})
        .get("schema", {})
    )

    def get_rows(tid):
        if tid in schema_info:
            return schema_info[tid].get("row_count")
        for key in schema_info:
            if tid == key.split(".")[-1] or tid == key:
                return schema_info[key].get("row_count")
        return None

    rows1 = get_rows(table_id_1)
    rows2 = get_rows(table_id_2)

    if rows1 is None or rows2 is None:
        return {
            "error": "Table(s) not found in schema cache or row_count missing.",
            "available_tables": list(schema_info.keys()),
        }

    return {
        "match": rows1 == rows2,
        "table_1": {"name": table_id_1, "row_count": rows1},
        "table_2": {"name": table_id_2, "row_count": rows2},
        "difference": abs(rows1 - rows2),
    }
