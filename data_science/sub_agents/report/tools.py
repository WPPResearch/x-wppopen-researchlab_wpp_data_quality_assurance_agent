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

"""Report generation tools for Markdown, HTML, and PDF formats."""

import json
import logging
import os
from datetime import datetime
from typing import Any

import markdown2
from fpdf import FPDF
from google.adk.agents.callback_context import CallbackContext
import google.genai.types as types
from google.adk.tools.bigquery.client import get_bigquery_client
from data_science.sub_agents.bigquery.tools import compute_project, USER_AGENT

logger = logging.getLogger(__name__)

# ruff: noqa: RUF001


def _generate_pdf_from_markdown(
    markdown_content: str,
    artifact_loader=None,
) -> bytes:
    """
    Generates a PDF file from markdown content and returns its binary content.

    Supports two image embedding methods:
    1. Base64 images: ![alt](data:image/png;base64,...)
    2. Artifact references: ![alt](artifact:filename.png) - fetches from session artifacts

    Args:
        markdown_content: The markdown text to convert
        artifact_loader: Optional async function to load artifacts by filename.
                        Should return (bytes, mime_type) or None if not found.
    """
    import base64
    import io
    import re
    import asyncio

    images = []

    # Pattern for base64 images: ![alt text](data:image/png;base64,...)
    base64_pattern = (
        r"!\[([^\]]*)\]\(data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)\)"
    )

    # Pattern for artifact references: ![alt text](artifact:filename.png)
    artifact_pattern = r"!\[([^\]]*)\]\(artifact:([^)]+)\)"

    def replace_base64_image(match):
        alt_text = match.group(1)
        img_format = match.group(2)
        img_data = match.group(3)
        placeholder = f"__IMAGE_PLACEHOLDER_{len(images)}__"
        images.append(
            {
                "alt": alt_text,
                "format": img_format,
                "data": img_data,
                "type": "base64",
                "placeholder": placeholder,
            },
        )
        return placeholder

    def replace_artifact_image(match):
        alt_text = match.group(1)
        filename = match.group(2)
        placeholder = f"__IMAGE_PLACEHOLDER_{len(images)}__"
        images.append(
            {
                "alt": alt_text or filename,
                "filename": filename,
                "type": "artifact",
                "placeholder": placeholder,
            },
        )
        return placeholder

    # Replace images with placeholders
    content_for_html = re.sub(base64_pattern, replace_base64_image, markdown_content)
    content_for_html = re.sub(
        artifact_pattern,
        replace_artifact_image,
        content_for_html,
    )

    # Convert markdown to HTML
    html_content = markdown2.markdown(content_for_html, extras=["tables"])

    # Handle common unicode characters that aren't in Latin-1
    replacements = {
        "—": "-",  # em-dash to hyphen
        "'": "'",  # smart quote to single quote
        """: '"',  # smart double quote
        """: '"',  # smart double quote
        "–": "-",  # en-dash
    }

    for unicode_char, ascii_char in replacements.items():
        html_content = html_content.replace(unicode_char, ascii_char)

    # Force encode/decode to strip remaining non-Latin-1 chars
    html_content = html_content.encode("latin-1", "replace").decode("latin-1")

    # Remove image placeholders from HTML (we'll add images separately)
    for img in images:
        html_content = html_content.replace(img["placeholder"], "")

    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    # Write HTML content
    styled_html = f'<span style="font-family: Helvetica">{html_content}</span>'
    pdf.write_html(styled_html)

    # Helper to add image to PDF with proper sizing
    def add_image_to_pdf(img_bytes, alt_text):
        from PIL import Image as PILImage

        img_buffer = io.BytesIO(img_bytes)
        pil_img = PILImage.open(io.BytesIO(img_bytes))
        img_width, img_height = pil_img.size

        # Calculate scaled dimensions (max width 180mm, max height 200mm)
        max_width_mm = 180
        max_height_mm = 200

        # Convert pixels to mm (assuming 96 DPI for screen images)
        dpi = 96
        width_mm = (img_width / dpi) * 25.4
        height_mm = (img_height / dpi) * 25.4

        # Scale to fit within max dimensions while maintaining aspect ratio
        scale = min(max_width_mm / width_mm, max_height_mm / height_mm, 1.0)
        final_width = width_mm * scale
        final_height = height_mm * scale

        # Add a new page for each image
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        if alt_text:
            pdf.cell(0, 10, alt_text, new_x="LMARGIN", new_y="NEXT", align="C")

        # Center the image horizontally
        page_width = 210  # A4 width in mm
        x_pos = (page_width - final_width) / 2

        img_buffer.seek(0)
        pdf.image(img_buffer, x=x_pos, y=pdf.get_y() + 5, w=final_width, h=final_height)

    # Process each image
    for i, img in enumerate(images):
        try:
            if img["type"] == "base64":
                # Handle base64 images
                b64_data = img["data"]
                missing_padding = len(b64_data) % 4
                if missing_padding:
                    b64_data += "=" * (4 - missing_padding)
                img_bytes = base64.b64decode(b64_data)
                add_image_to_pdf(img_bytes, img["alt"])

            elif img["type"] == "artifact" and artifact_loader:
                # Handle artifact references - fetch from session
                try:
                    # Run the async loader
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in an async context, need to use a different approach
                        import concurrent.futures

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                artifact_loader(img["filename"]),
                            )
                            result = future.result(timeout=10)
                    else:
                        result = asyncio.run(artifact_loader(img["filename"]))

                    if result:
                        img_bytes, mime_type = result
                        add_image_to_pdf(img_bytes, img["alt"])
                    else:
                        pdf.add_page()
                        pdf.multi_cell(
                            0,
                            10,
                            f"[Artifact '{img['filename']}' not found]",
                        )
                except Exception as e:
                    pdf.add_page()
                    pdf.multi_cell(
                        0,
                        10,
                        f"[Error loading artifact '{img['filename']}': {e}]",
                    )
            elif img["type"] == "artifact":
                # No artifact loader provided
                pdf.add_page()
                pdf.multi_cell(
                    0,
                    10,
                    f"[Artifact '{img['filename']}' - loader not available]",
                )

        except Exception as e:
            pdf.multi_cell(0, 10, f"[Image {i + 1} could not be rendered: {e}]")

    return bytes(pdf.output())


def _generate_html_from_markdown(markdown_content: str) -> str:
    """
    Generates a complete HTML document from markdown content.
    """
    html_body = markdown2.markdown(
        markdown_content,
        extras=["tables", "fenced-code-blocks", "code-friendly"],
    )

    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Science Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }}
        h1, h2, h3 {{ color: #1a1a2e; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 0.75rem;
            text-align: left;
        }}
        th {{ background-color: #f4f4f4; }}
        tr:nth-child(even) {{ background-color: #fafafa; }}
        img {{ max-width: 100%; height: auto; }}
        code {{
            background-color: #f4f4f4;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""
    return html_document


async def save_report_markdown(
    content_to_save: str,
    filename: str = "report.md",
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Saves the provided content as a Markdown file artifact.

    Args:
        content_to_save: The Markdown content of the report.
        filename: The name of the file to save (default: "report.md").
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with status and message about the saved file.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot save artifact.",
        }

    # Ensure filename has .md extension
    if not filename.endswith(".md"):
        filename = filename.rsplit(".", 1)[0] + ".md"

    content_bytes = content_to_save.encode("utf-8")
    artifact_part = types.Part(
        inline_data=types.Blob(data=content_bytes, mime_type="text/markdown"),
    )

    version = await tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )

    return {
        "status": "success",
        "format": "markdown",
        "message": f"Markdown file '{filename}' (version {version}) saved successfully.",
    }


async def save_json_statistical_report(
    content_to_save: str,
    filename: str = "report.json",
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Saves the JSON statistical analysis result as a .json file artifact.
    The filename is automatically derived from the table name in the report
    if the default filename is used.

    Args:
        content_to_save: The JSON string content to save.
        filename: Filename for the artifact. Defaults to "report.json" but will be
                 overridden by the table name from content if possible.
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with status and message about the saved file.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot save artifact.",
        }

    # Try to use the table name for the filename
    try:
        import json

        table_name = json.loads(content_to_save)["report_metadata"]["table_name"]
        filename = f"{table_name.replace('.', '_')}.json"
    except Exception:
        pass  # Fallback to the provided filename (defaults to "report.json")

    # Final extension check
    if not filename.lower().endswith(".json"):
        filename += ".json"

    content_bytes = content_to_save.encode("utf-8")
    artifact_part = types.Part(
        inline_data=types.Blob(data=content_bytes, mime_type="application/json"),
    )

    version = await tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )

    result = {
        "status": "success",
        "format": "json",
        "message": f"JSON file '{filename}' (version {version}) saved successfully.",
    }

    # Direct GCS upload for guaranteed bucket persistence
    bucket_name = os.environ.get("ARTIFACT_BUCKET_NAME")
    if bucket_name:
        try:
            from google.cloud import storage

            gcs_client = storage.Client()
            bucket = gcs_client.bucket(bucket_name)
            session = getattr(tool_context, "session", None)
            session_id = getattr(session, "id", None) or "unknown_session"
            blob_path = f"json_reports/{session_id}/{filename}"
            blob = bucket.blob(blob_path)
            blob.upload_from_string(content_to_save, content_type="application/json")
            gcs_uri = f"gs://{bucket_name}/{blob_path}"
            result["gcs_uri"] = gcs_uri
            result["message"] += f" Also uploaded to GCS: {gcs_uri}"
            logger.info(f"JSON report uploaded to GCS: {gcs_uri}")
        except Exception as e:
            logger.warning(f"Direct GCS upload failed for '{filename}': {e}")
            result["gcs_upload_error"] = str(e)

    return result


async def save_report_html(
    content_to_save: str,
    filename: str = "report.html",
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Converts Markdown content to HTML and saves it as an HTML file artifact.

    Args:
        content_to_save: The Markdown content of the report.
        filename: The name of the file to save (default: "report.html").
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with status and message about the saved file.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot save artifact.",
        }

    # Ensure filename has .html extension
    if not filename.endswith(".html"):
        filename = filename.rsplit(".", 1)[0] + ".html"

    html_content = _generate_html_from_markdown(content_to_save)
    content_bytes = html_content.encode("utf-8")

    artifact_part = types.Part(
        inline_data=types.Blob(data=content_bytes, mime_type="text/html"),
    )

    version = await tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )

    return {
        "status": "success",
        "format": "html",
        "message": f"HTML file '{filename}' (version {version}) saved successfully.",
    }


async def save_report_pdf(
    content_to_save: str,
    filename: str = "report.pdf",
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Converts Markdown content to PDF and saves it as a PDF file artifact.

    Supports embedding images via:
    - Base64: ![alt](data:image/png;base64,...)
    - Artifact reference: ![alt](artifact:filename.png) - fetches from session

    Args:
        content_to_save: The Markdown content of the report.
        filename: The name of the file to save (default: "report.pdf").
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with status and message about the saved file.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot save artifact.",
        }

    # Ensure filename has .pdf extension
    if not filename.endswith(".pdf"):
        filename = filename.rsplit(".", 1)[0] + ".pdf"

    # Create an artifact loader function for fetching session artifacts
    async def artifact_loader(artifact_filename: str):
        """Load an artifact from the session and return (bytes, mime_type)."""
        try:
            artifact = await tool_context.load_artifact(artifact_filename)
            if artifact and artifact.inline_data:
                return (artifact.inline_data.data, artifact.inline_data.mime_type)
            return None
        except Exception:
            return None

    content_bytes = _generate_pdf_from_markdown(content_to_save, artifact_loader)
    artifact_part = types.Part.from_bytes(
        data=content_bytes,
        mime_type="application/pdf",
    )

    version = await tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )

    return {
        "status": "success",
        "format": "pdf",
        "message": f"PDF file '{filename}' (version {version}) saved successfully.",
    }


async def list_session_artifacts(
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Lists all artifacts available in the current session.
    Use this to see what images, plots, or data files are available from previous queries.

    Args:
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with the list of available artifact filenames and their versions.
    """

    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot list artifacts.",
        }

    try:
        # List all artifacts in the session
        artifact_keys = await tool_context.list_artifacts()

        artifacts_info = []
        for key in artifact_keys:
            # Try to get artifact info
            artifact = await tool_context.load_artifact(key)
            if artifact and artifact.inline_data:
                artifacts_info.append(
                    {
                        "filename": key,
                        "mime_type": artifact.inline_data.mime_type,
                        "size_bytes": len(artifact.inline_data.data)
                        if artifact.inline_data.data
                        else 0,
                    },
                )

        return {
            "status": "success",
            "count": len(artifacts_info),
            "artifacts": artifacts_info,
            "message": f"Found {len(artifacts_info)} artifact(s) in the session.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing artifacts: {str(e)}",
        }


async def get_artifact_as_base64(
    filename: str,
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Retrieves an artifact (image, plot, etc.) from the session and returns it as a base64 string.

    WARNING: This tool is DEPRECATED for report generation because base64 strings consume
    massive amounts of tokens. Instead, use the artifact reference syntax in your markdown:
    ![Description](artifact:filename.png)

    Only use this tool if you absolutely need to analyze the image content or if
    artifact references are not supported in your output format.

    Args:
        filename: The name of the artifact file to retrieve.
        tool_context: The tool context provided by the ADK.
    """
    import base64

    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot load artifact.",
        }

    try:
        artifact = await tool_context.load_artifact(filename)

        if artifact is None:
            return {
                "status": "error",
                "message": f"Artifact '{filename}' not found in session.",
            }

        if artifact.inline_data is None:
            return {
                "status": "error",
                "message": f"Artifact '{filename}' has no inline data.",
            }

        # Encode to base64
        content_bytes = artifact.inline_data.data
        base64_string = base64.b64encode(content_bytes).decode("utf-8")
        mime_type = artifact.inline_data.mime_type or "application/octet-stream"

        # Determine if it's an image
        is_image = mime_type.startswith("image/")

        result = {
            "status": "success",
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": len(content_bytes),
            "base64": base64_string,
        }

        if is_image:
            result["embed_markdown"] = (
                f"![{filename}](data:{mime_type};base64,{base64_string})"
            )
            result["message"] = (
                f"Image '{filename}' retrieved. Use embed_markdown to include in report."
            )
        else:
            result["message"] = f"Artifact '{filename}' retrieved as base64."

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error loading artifact: {str(e)}",
        }


async def json_statistical_analysis(
    table_id: str,
    save_to_artifact: bool = True,
    tool_context: CallbackContext = None,
) -> Any:
    """
    Generates a comprehensive JSON report for a BigQuery table.

    Includes:
    - Metadata (table name, generation time, total rows)
    - Schema summary (column count and names)
    - Numerical column statistics (mean, std, min, max)
    - Categorical column distributions (top 5 classes and percentages)

    Args:
        table_id: The table ID to analyze (can be full or short name).
        save_to_artifact: If True, saves the JSON report as an artifact.
        tool_context: The tool context provided by the ADK.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing.",
        }

    schema_info = (
        tool_context.state.get("database_settings", {})
        .get("bigquery", {})
        .get("schema", {})
    )

    def get_table_details(tid):
        if tid in schema_info:
            return tid, schema_info[tid]
        for key in schema_info:
            if tid == key.split(".")[-1] or tid == key:
                return key, schema_info[key]
        return None, None

    full_id, table_details = get_table_details(table_id)

    if not full_id or not table_details:
        return {
            "status": "error",
            "message": f"Table '{table_id}' not found in schema cache.",
            "available_tables": list(schema_info.keys()),
        }

    total_rows = table_details.get("row_count", 0)
    schema_fields = table_details.get("table_schema", [])

    # Exclude specific types to simplify the report (e.g., DATE)
    EXCLUDED_TYPES = ["DATE", "DATETIME", "TIMESTAMP"]
    schema_fields = [f for f in schema_fields if f[1].upper() not in EXCLUDED_TYPES]

    column_names = [field[0] for field in schema_fields]
    # Initialize the report structure
    report = {
        "report_metadata": {
            "table_name": full_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "high_cardinality_columns": [],
        },
        "schema_summary": {
            "total_rows": total_rows,
            "number_of_columns": len(column_names),
            "column_names": column_names,
        },
        "numerical_columns": [],
        "categorical_columns": [],
    }

    # Separate columns by type
    numeric_types = ["INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC", "INTEGER", "FLOAT"]
    numerical_cols = []
    categorical_cols = []

    for field in schema_fields:
        col_name = field[0]
        col_type = field[1].upper()
        # If column name ends with _id, it's categorical even if numeric
        if col_name.lower().endswith("_id"):
            categorical_cols.append(col_name)
        elif col_type in numeric_types:
            numerical_cols.append(col_name)
        else:
            categorical_cols.append(col_name)

    client = get_bigquery_client(
        project=compute_project,
        credentials=None,
        user_agent=USER_AGENT,
    )

    # 1. Numerical Statistics
    if numerical_cols:
        stats_queries = []
        for col in numerical_cols:
            stats_queries.append(
                f"""
            SELECT
                '{col}' as column_name,
                AVG({col}) as mean,
                STDDEV({col}) as std,
                MIN({col}) as min,
                MAX({col}) as max,
                COUNTIF({col} IS NULL) as null_count
            FROM `{full_id}`
            """,
            )

        full_query = " UNION ALL ".join(stats_queries)
        try:
            df = client.query(full_query).to_dataframe()
            for _, row in df.iterrows():
                report["numerical_columns"].append(
                    {
                        "column_name": row["column_name"],
                        "stats": {
                            "max": round(float(row["max"]), 4)
                            if row["max"] is not None
                            else 0.0,
                            "min": round(float(row["min"]), 4)
                            if row["min"] is not None
                            else 0.0,
                            "mean": round(float(row["mean"]), 4)
                            if row["mean"] is not None
                            else 0.0,
                            "std": round(float(row["std"]), 4)
                            if row["std"] is not None
                            else 0.0,
                            "null_count": int(row["null_count"]),
                        },
                    },
                )
        except Exception as e:
            logger.error(f"Error fetching numerical stats for {full_id}: {e}")

    # 2. Categorical Distributions
    for col in categorical_cols:
        # Use SAFE_CAST to STRING for ID columns to ensure they are handled as text
        col_expr = f"SAFE_CAST({col} AS STRING)" if col.lower().endswith("_id") else col

        # Combined query for distribution, null count, and distinct classes
        combined_query = f"""
        WITH basic_stats AS (
            SELECT
                COUNTIF({col_expr} IS NULL) as null_count,
                COUNT(DISTINCT {col_expr}) as num_classes
            FROM `{full_id}`
        ),
        dist AS (
            SELECT
                {col_expr} as class_name,
                COUNT(*) as count,
                ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2) as percentage
            FROM `{full_id}`
            WHERE {col_expr} IS NOT NULL
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 5
        )
        SELECT * FROM basic_stats LEFT JOIN dist ON TRUE
        """
        try:
            res_df = client.query(combined_query).to_dataframe()
            if not res_df.empty:
                null_count = int(res_df.iloc[0]["null_count"])
                num_classes = int(res_df.iloc[0]["num_classes"])

                # High cardinality detection - Absolute threshold > 50
                is_high_cardinality = num_classes > 50

                if is_high_cardinality:
                    report["report_metadata"]["high_cardinality_columns"].append(col)
                    report["categorical_columns"].append(
                        {
                            "column_name": col,
                            "number_of_classes": num_classes,
                            "null_count": null_count,
                            "note": "High cardinality detected - detailed distribution skipped for brevity.",
                        },
                    )
                    continue

                classes = []
                for _, row in res_df.iterrows():
                    if row["class_name"] is not None:
                        classes.append(
                            {
                                "class_name": str(row["class_name"]),
                                "count": int(row["count"]),
                                "percentage": float(row["percentage"]),
                            },
                        )

                report["categorical_columns"].append(
                    {
                        "column_name": col,
                        "number_of_classes": num_classes,
                        "null_count": null_count,
                        "class_distribution": classes,
                    },
                )
        except Exception as e:
            logger.error(
                f"Error fetching categorical stats for column {col} in {full_id}: {e}",
            )

    report_json = json.dumps(report, indent=2)

    if save_to_artifact and tool_context:
        save_result = await save_json_statistical_report(
            content_to_save=report_json,
            tool_context=tool_context,
        )
        if save_result.get("status") == "success":
            return f"Analysis complete for {table_id}. {save_result.get('message')}"
        return f"Analysis complete for {table_id}, but saving failed: {save_result.get('message')}"

    return report_json
