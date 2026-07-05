"""tool-005 – File Reader (dummy implementation)."""

from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class FileReaderTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-005"

    def name(self) -> str:
        return "File Reader"

    def description(self) -> str:
        return "Read files from local storage or cloud (S3, GCS, Azure Blob)"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        path = input_data.get("path", "data/input.json")
        storage_type = input_data.get("storage_type", "local")
        encoding = input_data.get("encoding", "utf-8")

        # Simulate reading a JSON data file
        content = {
            "source_file": path,
            "storage_type": storage_type,
            "encoding": encoding,
            "records": [
                {"id": "1", "name": "Alice Johnson", "email": "alice@example.com", "status": "active"},
                {"id": "2", "name": "Bob Smith", "email": "bob@example.com", "status": "pending"},
                {"id": "3", "name": "Carol White", "email": "carol@example.com", "status": "active"},
            ],
            "size_bytes": 1024,
            "line_count": 3,
        }

        return {
            "file_read": True,
            "path": path,
            "storage_type": storage_type,
            "records": content["records"],
            "metadata": {
                "size_bytes": content["size_bytes"],
                "line_count": content["line_count"],
            },
        }


Registry.register_tool(FileReaderTool())
