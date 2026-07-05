"""Unit tests for JSON-schema + args-model building."""
from app.domain.tool import ToolParameter
from app.registry.schema_builder import build_args_model, build_input_schema


def _params():
    return [
        ToolParameter(name="to", type="string or list", required=True),
        ToolParameter(name="count", type="integer", required=False, default=1),
        ToolParameter(name="flag", type="bool", required=False, default=False),
    ]


def test_input_schema_types_and_required():
    schema = build_input_schema(_params())
    assert schema["type"] == "object"
    assert schema["properties"]["to"]["type"] == "string"      # first recognised token
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["flag"]["type"] == "boolean"
    assert schema["required"] == ["to"]


def test_args_model_validates():
    model = build_args_model("outlook.send_email", _params())
    instance = model(to="x@y.com")
    assert instance.to == "x@y.com"
    assert instance.count == 1
