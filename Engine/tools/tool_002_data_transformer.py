"""tool-002 – Data Transformer (dummy implementation)."""

from typing import Any, Dict

from core.base_tool import BaseTool
from core.registry import Registry


class DataTransformerTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "tool-002"

    def name(self) -> str:
        return "Data Transformer"

    def description(self) -> str:
        return "Transform and map data between JSON, CSV, and XML formats"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        in_fmt = input_data.get("input_format", "json")
        out_fmt = input_data.get("output_format", "json")
        records = input_data.get("records", input_data.get("response_body", {}).get("data", []))

        transformed = []
        for idx, rec in enumerate(records if isinstance(records, list) else []):
            transformed.append(
                {
                    "row_index": idx,
                    "original": rec,
                    "transformed": {k: str(v).strip() for k, v in rec.items()}
                    if isinstance(rec, dict)
                    else str(rec),
                }
            )

        return {
            "transform_status": "success",
            "input_format": in_fmt,
            "output_format": out_fmt,
            "rows_in": len(records) if isinstance(records, list) else 0,
            "rows_out": len(transformed),
            "transformed_records": transformed,
            "mapping_applied": bool(input_data.get("mapping_rules")),
        }


Registry.register_tool(DataTransformerTool())
