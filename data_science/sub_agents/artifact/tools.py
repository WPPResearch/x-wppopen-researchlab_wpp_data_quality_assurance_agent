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

"""Tools for the Artifact Manager Agent."""

import base64
import logging
from typing import Any

from google.adk.agents.callback_context import CallbackContext
import google.genai.types as types

logger = logging.getLogger(__name__)


async def save_file_artifact(
    content: str,
    filename: str,
    mime_type: str = "",
    is_base64: bool = False,
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Save any file as an artifact for later retrieval.

    Use this to save images, plots, CSV data, JSON files, PDFs, or any other content
    that should be persisted in the session. Saved artifacts can be retrieved
    with the built-in load_artifacts tool or included in reports.

    Args:
        content: The file content. For text files, provide the text directly.
                 For binary files (images, PDFs), provide base64-encoded data
                 and set is_base64=True.
        filename: The name to save the file as (e.g., "chart.png", "data.csv", "report.pdf").
        mime_type: The MIME type of the file. If not provided, it will be
                   automatically detected from the filename extension.
        is_base64: Set to True if the content is base64 encoded (for binary files).
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with status and message about the saved artifact.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot save artifact.",
        }

    # Auto-detect mime_type from filename extension if not provided
    if not mime_type:
        extension_to_mime = {
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".html": "text/html",
            ".md": "text/markdown",
            ".xml": "application/xml",
        }
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime_type = extension_to_mime.get(ext, "text/plain")

    try:
        # Decode base64 if needed, otherwise encode text to bytes
        if is_base64:
            content_bytes = base64.b64decode(content)
        else:
            if isinstance(content, bytes):
                content_bytes = content
            else:
                content_bytes = content.encode("utf-8")

        binary_mime_types = {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/gif",
            "application/octet-stream",
        }
        is_binary = (
            is_base64 or mime_type in binary_mime_types or isinstance(content, bytes)
        )

        if is_binary:
            artifact_part = types.Part.from_bytes(
                data=content_bytes,
                mime_type=mime_type,
            )
        else:
            artifact_part = types.Part(
                inline_data=types.Blob(data=content_bytes, mime_type=mime_type),
            )

        version = await tool_context.save_artifact(
            filename=filename,
            artifact=artifact_part,
        )

        return {
            "status": "success",
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": len(content_bytes),
            "version": version,
            "message": f"Artifact '{filename}' (version {version}) saved successfully.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error saving artifact: {str(e)}",
        }


async def save_file_from_chat(
    filename: str,
    file_index: int = 0,
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    Save a file (image, PDF, or any binary) sent in the chat as an artifact.

    Use this when a user uploads a file directly in the chat and asks you to
    save it. This tool extracts the file bytes directly from the conversation
    history and saves them as an artifact — no base64 string is ever created,
    which saves tokens significantly.

    Supports images (PNG, JPEG, GIF, WebP), PDFs, and any other file type
    that is sent as inline data in the conversation.

    Args:
        filename: The name to save the file as (e.g., "photo.png", "report.pdf").
        file_index: Which file to save if multiple were sent. 0 = most recent
                    file in the conversation, 1 = second most recent, etc.
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with status and metadata about the saved artifact.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot save artifact.",
        }

    try:
        # Walk session events in reverse to find parts with inline_data
        file_parts_found = []
        for event in reversed(tool_context.session.events):
            if not hasattr(event, "content") or event.content is None:
                continue
            if not hasattr(event.content, "parts") or event.content.parts is None:
                continue
            for part in event.content.parts:
                if (
                    hasattr(part, "inline_data")
                    and part.inline_data is not None
                    and part.inline_data.data is not None
                    and part.inline_data.mime_type is not None
                ):
                    file_parts_found.append(part)

        if not file_parts_found:
            return {
                "status": "error",
                "message": (
                    "No files found in the conversation history. "
                    "The user must upload a file in the chat first."
                ),
            }

        if file_index >= len(file_parts_found):
            return {
                "status": "error",
                "message": (
                    f"File index {file_index} out of range. "
                    f"Found {len(file_parts_found)} file(s) in the conversation. "
                    f"Use file_index 0 to {len(file_parts_found) - 1}."
                ),
            }

        selected_part = file_parts_found[file_index]
        file_bytes = selected_part.inline_data.data
        mime_type = selected_part.inline_data.mime_type

        # Auto-fix filename extension if it has none
        mime_to_ext = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "application/pdf": ".pdf",
            "text/csv": ".csv",
            "application/json": ".json",
            "text/plain": ".txt",
        }
        if "." not in filename:
            expected_ext = mime_to_ext.get(mime_type, "")
            if expected_ext:
                filename = filename + expected_ext
                logger.info("Auto-added extension: %s", filename)

        # Save directly — no base64 encoding in the conversation
        artifact_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type,
        )

        version = await tool_context.save_artifact(
            filename=filename,
            artifact=artifact_part,
        )

        return {
            "status": "success",
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": len(file_bytes),
            "version": version,
            "message": (
                f"File saved as artifact '{filename}' (version {version}). "
                f"Bytes were extracted directly from the conversation — "
                f"no base64 encoding used."
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error saving file from chat: {str(e)}",
        }


async def list_all_artifacts(
    tool_context: CallbackContext = None,
) -> dict[str, Any]:
    """
    List all artifacts available in the current session.

    Use this to see what files, images, plots, or data have been saved
    during the session. This helps identify what can be loaded or
    included in reports.

    Args:
        tool_context: The tool context provided by the ADK.

    Returns:
        A dictionary with the list of available artifacts and their metadata.
    """
    if tool_context is None:
        return {
            "status": "error",
            "message": "Tool context is missing, cannot list artifacts.",
        }

    try:
        artifact_keys = await tool_context.list_artifacts()

        artifacts_info = []
        for key in artifact_keys:
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
