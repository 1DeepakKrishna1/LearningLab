"""tool-009 – CSV Exporter (dummy implementation)."""

import io
import csv
from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class CsvExporterTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-009"

    def name(self) -> str:
        return "CSV Exporter"

    def description(self) -> str:
        return "Export processed data to CSV format for downstream use"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        delimiter = input_data.get("delimiter", ",")
        include_headers = input_data.get("include_headers", True)
        output_path = input_data.get("output_path", "output/export.csv")

        records = input_data.get(
            "transformed_records",
            input_data.get("records", [{"id": 1, "value": "sample"}]),
        )

        # Produce CSV string in-memory
        buf = io.StringIO()
        if records:
            flat = [
                r.get("transformed", r) if isinstance(r, dict) else {"value": r}
                for r in records
            ]
            flat_dicts = [f if isinstance(f, dict) else {"value": f} for f in flat]
            writer = csv.DictWriter(
                buf,
                fieldnames=list(flat_dicts[0].keys()),
                delimiter=delimiter,
            )
            if include_headers:
                writer.writeheader()
            writer.writerows(flat_dicts)

        csv_preview = buf.getvalue()[:500]

        return {
            "export_status": "success",
            "output_path": output_path,
            "rows_exported": len(records),
            "delimiter": delimiter,
            "csv_preview": csv_preview,
            "size_bytes": len(csv_preview.encode()),
        }


Registry.register_tool(CsvExporterTool())
