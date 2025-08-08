"""
Tool for retrieving detailed information about a specific RAG corpus.
"""

from google.adk.tools.tool_context import ToolContext
from vertexai import rag

from .utils import check_corpus_exists, get_corpus_resource_name

from typing import Optional

def get_corpus_info(
    corpus_name: str,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """
    Get detailed information about a specific RAG corpus, including its files.

    Args:
        corpus_name (str): The full resource name of the corpus to get information about.
                           Preferably use the resource_name from list_corpora results.
        tool_context (ToolContext, optional): The tool context for state checks.

    Returns:
        dict: Information about the corpus and its files
    """
    try:
        # Check if corpus exists (only if tool_context is provided)
        if tool_context and not check_corpus_exists(corpus_name, tool_context):
            return {
                "status": "error",
                "message": f"Corpus '{corpus_name}' does not exist",
                "corpus_name": corpus_name,
            }

        # Get the corpus resource name
        corpus_resource_name = get_corpus_resource_name(corpus_name)

        # Default display name to the corpus name
        corpus_display_name = corpus_name

        file_details = []

        try:
            # Get list of files
            files = rag.list_files(corpus_resource_name)
            for rag_file in files:
                try:
                    file_id = rag_file.name.split("/")[-1]

                    file_info = {
                        "file_id": file_id,
                        "display_name": getattr(rag_file, "display_name", ""),
                        "source_uri": getattr(rag_file, "source_uri", ""),
                        "create_time": str(getattr(rag_file, "create_time", "")),
                        "update_time": str(getattr(rag_file, "update_time", "")),
                    }

                    file_details.append(file_info)
                except Exception:
                    continue
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Successfully retrieved information for corpus '{corpus_display_name}'",
            "corpus_name": corpus_name,
            "corpus_display_name": corpus_display_name,
            "file_count": len(file_details),
            "files": file_details,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting corpus information: {str(e)}",
            "corpus_name": corpus_name,
        }
