import json
from typing import List
from langchain.prompts import PromptTemplate
from langchain.tools import tool
# from langchain_core.language_models import BaseLanguageModel  # if you want to type the llm param


def build_tools_from_config(
    config_json: str,
    llm,               # your LLM instance (e.g. ChatOpenAI / ChatAnthropic / etc.)
    json_string: str,  # the knowledge graph JSON (or you can pass it per-call instead)
):
    """
    Build a list of LangChain tools from a JSON configuration.
    
    - config_json: JSON string with 'tools' list
    - llm:         LLM instance used in the chain
    - json_string: Knowledge graph JSON (shared for all tools here)
    """
    config = json.loads(config_json)
    tools = []

    for tool_conf in config.get("tools", []):
        name = tool_conf["name"]
        description = tool_conf["description"]
        template_str = tool_conf["prompt_template"]

        # Close over values to avoid late-binding issues in the loop
        def make_tool(_name, _description, _template_str):
            @tool(_name)
            def generated_tool(query: str) -> str:
                """Dynamic tool, description is injected below."""
                prompt = PromptTemplate(
                    input_variables=["json_string", "question"],
                    template=_template_str,
                )
                qa_chain = prompt | llm
                return qa_chain.invoke({
                    "json_string": json_string,
                    "question": query,
                })

            # Dynamic docstring acts as tool description / annotation
            generated_tool.__doc__ = _description
            return generated_tool

        tools.append(make_tool(name, description, template_str))

    return tools

# 1. Your config JSON (you can load it from a file, DB, API, etc.)
config_json = """
{
  "tools": [
    {
      "name": "Knowledge Graph Overview",
      "description": "Use this tool to answer questions related to the medical knowledge graph.",
      "prompt_template": "
        You are an expert AI analyst working with a structured medical knowledge graph in JSON.

        Given the following JSON knowledge graph:

        {json_string}

        User's question: {question}

        Provide a clear and concise answer.
      "
    },
    {
      "name": 'Drug Interaction Graph',
      "description": "Use this tool to answer questions about drug–drug interactions from the graph.",
      "prompt_template": "
        You are an expert assistant for drug–drug interactions.

        Knowledge graph:

        {json_string}

        Question: {question}

        Provide a short interaction summary and warnings if any.
      "
    }
  ]
}
"""

# 2. Suppose you already have:
# llm = ChatOpenAI(...)
# json_string = "<your medical KG JSON>"

tools = build_tools_from_config(config_json, llm, json_string)

# Now `tools` is a list of LangChain Tool objects; you can pass them to your agent:
# agent = create_tool_calling_agent(llm, tools, ...)
