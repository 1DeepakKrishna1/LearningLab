from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from langchain.tools import tool

# Assume you already have an LLM instance
# llm = ...

def build_kg_tools(configs: List[Dict[str, Any]], llm) -> List[Any]:
    """
    Build multiple LangChain tools from a list of config dicts.

    Each config should have:
    - name: str                       -> tool name
    - description: str                -> tool description (used as docstring)
    - prompt_instructions: str        -> high-level instructions for the tool
    - json_string: str                -> the knowledge graph JSON (as string)
    """
    tools = []

    for cfg in configs:
        name: str = cfg["name"]
        description: str = cfg["description"]
        prompt_instructions: str = cfg["prompt_instructions"]
        json_string: str = cfg["json_string"]

        # Build the prompt *per tool* using config values
        template = f"""
        {prompt_instructions}

        Given the following JSON knowledge graph:

        {{json_string}}

        User's question: {{question}}

        Provide a clear, concise, and accurate answer based ONLY on the graph.
        """

        prompt = PromptTemplate(
            input_variables=["json_string", "question"],
            template=template,
        )

        qa_chain = prompt | llm

        # Use default args in the inner function to freeze loop variables
        @tool(name)
        def generated_tool(
            query: str,
            _qa_chain=qa_chain,
            _json_string=json_string,
            _description=description,
        ) -> str:
            """Dynamically generated tool."""
            return _qa_chain.invoke(
                {
                    "json_string": _json_string,
                    "question": query,
                }
            )

        # Dynamic docstring becomes the tool's description for the model
        generated_tool.__doc__ = description
        # Optional: set a cleaner python function name
        generated_tool.__name__ = name.lower().replace(" ", "_")

        tools.append(generated_tool)

    return tools


# This could be loaded from a JSON file instead
tool_configs = [
    {
        "name": "Knowledge Graph Overview",
        "description": "Use this tool to answer generic questions about the medical knowledge graph.",
        "prompt_instructions": """
        You are an expert AI analyst working with a structured medical knowledge graph in JSON format.
        Extract concise answers based on entities and relationships in the graph.
        """,
        "json_string": medical_kg_json,  # your JSON string here
    },
    {
        "name": "Drug Interaction Checker",
        "description": "Use this tool to answer questions about drug-drug interactions using the interaction graph.",
        "prompt_instructions": """
        You are an expert on drug interactions. Use the JSON graph to check interactions between drugs
        and provide a short, clinically relevant explanation.
        """,
        "json_string": drug_interaction_kg_json,  # another JSON string
    },
    {
        "name": "Disease Symptom Explorer",
        "description": "Use this tool to map diseases to their symptoms and related conditions.",
        "prompt_instructions": """
        You are an expert clinical knowledge explorer. Use the JSON graph to map diseases, symptoms,
        risk factors, and related conditions. Answer in simple, clear language.
        """,
        "json_string": disease_symptom_kg_json,
    },
]

# Build all tools in one shot
kg_tools = build_kg_tools(tool_configs, llm)

# You can then pass `kg_tools` into your agent/tool list, e.g.
# agent = create_react_agent(llm, tools=kg_tools)

cfg = {
    "name": "Knowledge Graph Overview",
    "description": "[domain: medical][kg_type: overview] Use this tool to answer generic questions...",
    "prompt_instructions": "...",
    "json_string": medical_kg_json,
}
