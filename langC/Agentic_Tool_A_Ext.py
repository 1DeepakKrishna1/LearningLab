from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from langchain.tools import tool
import requests
from bs4 import BeautifulSoup


def build_dynamic_tools(configs: List[Dict[str, Any]], llm) -> List[Any]:
    """
    Build multiple LangChain tools from a list of config dicts.

    Common keys:
    - name: str
    - description: str
    - type: str            -> "kg_qa" | "rest_api" | "web_scrape" (extensible)
    - prompt_instructions: str (for LLM-based tools)
    - plus type-specific keys (see below)
    """
    tools = []

    for cfg in configs:
        name: str = cfg["name"]
        description: str = cfg["description"]
        tool_type: str = cfg["type"]

        # ---------- 1) JSON KG QA (your existing pattern) ----------
        if tool_type == "kg_qa":
            prompt_instructions: str = cfg["prompt_instructions"]
            json_string: str = cfg["json_string"]

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

            @tool(name)
            def kg_tool(
                query: str,
                _qa_chain=qa_chain,
                _json_string=json_string,
                _description=description,
            ) -> str:
                """Dynamically generated KG QA tool."""
                return _qa_chain.invoke(
                    {
                        "json_string": _json_string,
                        "question": query,
                    }
                )

            kg_tool.__doc__ = description
            kg_tool.__name__ = name.lower().replace(" ", "_")
            tools.append(kg_tool)

        # ---------- 2) REST API tool ----------
        elif tool_type == "rest_api":
            # Type-specific config:
            # - method: "GET" | "POST" | ...
            # - url: base URL or full endpoint
            # - query_param_name: how to map the tool's `query` arg into the request
            # - default_params: optional dict of fixed params
            # - headers: optional dict headers
            method: str = cfg.get("method", "GET").upper()
            url: str = cfg["url"]
            query_param_name: str = cfg.get("query_param_name", "q")
            default_params: Dict[str, Any] = cfg.get("default_params", {})
            headers: Dict[str, str] = cfg.get("headers", {})

            @tool(name)
            def api_tool(
                query: str,
                _url=url,
                _method=method,
                _query_param_name=query_param_name,
                _default_params=default_params,
                _headers=headers,
                _description=description,
            ) -> str:
                """Dynamically generated REST API tool."""
                try:
                    params = dict(_default_params)
                    # Put the user query into a param (if set)
                    if _query_param_name:
                        params[_query_param_name] = query

                    if _method == "GET":
                        resp = requests.get(_url, params=params, headers=_headers, timeout=10)
                    else:
                        resp = requests.request(
                            _method, _url, params=params, headers=_headers, timeout=10
                        )

                    resp.raise_for_status()
                    # Return JSON if possible, otherwise text
                    try:
                        return resp.json()
                    except ValueError:
                        return resp.text
                except Exception as e:
                    return f"API call failed: {e}"

            api_tool.__doc__ = description
            api_tool.__name__ = name.lower().replace(" ", "_")
            tools.append(api_tool)

        # ---------- 3) Web scraping / portal extract tool ----------
        elif tool_type == "web_scrape":
            # Type-specific config:
            # - url_template: e.g. "https://example.com/search?q={query}"
            # - css_selector: optional; if provided, only extract matching elements
            # - prompt_instructions: how LLM should process extracted HTML/text
            url_template: str = cfg["url_template"]
            css_selector: str = cfg.get("css_selector", "")
            prompt_instructions: str = cfg.get(
                "prompt_instructions",
                "Summarize the following page content and answer the user's question.",
            )

            # Prompt for post-processing scraped text with the LLM
            scrape_template = f"""
            {prompt_instructions}

            Page content:
            {{page_text}} 

            User's question:
            {{question}}

            Provide a concise answer based ONLY on the content above.
            """

            scrape_prompt = PromptTemplate(
                input_variables=["page_text", "question"],
                template=scrape_template,
            )
            scrape_chain = scrape_prompt | llm

            @tool(name)
            def web_scrape_tool(
                query: str,
                _url_template=url_template,
                _css_selector=css_selector,
                _scrape_chain=scrape_chain,
                _description=description,
            ) -> str:
                """Dynamically generated web scraping tool."""
                try:
                    url = _url_template.format(query=query)
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()

                    soup = BeautifulSoup(resp.text, "html.parser")
                    if _css_selector:
                        elements = soup.select(_css_selector)
                        text = "\n".join(el.get_text(strip=True) for el in elements)
                    else:
                        text = soup.get_text(separator="\n", strip=True)

                    # Feed scraped text to LLM for structured answer
                    return _scrape_chain.invoke(
                        {
                            "page_text": text[:15000],  # keep it bounded
                            "question": query,
                        }
                    )
                except Exception as e:
                    return f"Web scraping failed: {e}"

            web_scrape_tool.__doc__ = description
            web_scrape_tool.__name__ = name.lower().replace(" ", "_")
            tools.append(web_scrape_tool)

        # ---------- 4) Unknown type ----------
        else:
            raise ValueError(f"Unsupported tool type: {tool_type}")

    return tools


# Existing KG JSON tools
# TODO Pre and Post Hooks
tool_configs = [
    {
        "name": "Knowledge Graph Overview",
        "description": "Use this tool to answer generic questions about the medical knowledge graph.",
        "type": "kg_qa",
        "prompt_instructions": """
        You are an expert AI analyst working with a structured medical knowledge graph in JSON format.
        Extract concise answers based on entities and relationships in the graph.
        """,
        "json_string": medical_kg_json,
    },
    {
        "name": "Drug Interaction Checker",
        "description": "Use this tool to answer questions about drug-drug interactions using the interaction graph.",
        "type": "kg_qa",
        "prompt_instructions": """
        You are an expert on drug interactions. Use the JSON graph to check interactions between drugs
        and provide a short, clinically relevant explanation.
        """,
        "json_string": drug_interaction_kg_json,
    },
    {
        "name": "Disease Symptom Explorer",
        "description": "Use this tool to map diseases to their symptoms and related conditions.",
        "type": "kg_qa",
        "prompt_instructions": """
        You are an expert clinical knowledge explorer. Use the JSON graph to map diseases, symptoms,
        risk factors, and related conditions. Answer in simple, clear language.
        """,
        "json_string": disease_symptom_kg_json,
    },

    # New: REST API-backed tool
    {
        "name": "Clinical Guidelines API",
        "description": "Fetch clinical guideline summaries from the hospital's REST API.",
        "type": "rest_api",
        "method": "GET",
        "url": "https://api.hospital.com/guidelines/search",
        "query_param_name": "q",
        "default_params": {"limit": 5},
        "headers": {"Authorization": "Bearer <TOKEN>"},
    },

    # New: Web portal scraping tool
    {
        "name": "Public Health Web Portal Search",
        "description": "Search and extract relevant information from the public health web portal.",
        "type": "web_scrape",
        "url_template": "https://www.publichealth-portal.gov/search?q={query}",
        "css_selector": ".article-body",  # or leave empty to take full page text
        "prompt_instructions": """
        You are summarizing information from the official public health portal.
        Use only the extracted page content to answer the question in clear, non-technical language.
        """,
    },
]

# Build all tools
all_tools = build_dynamic_tools(tool_configs, llm)

#from typing import List, Dict, Any
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate


def build_domain_agent(domain_cfg: Dict[str, Any], llm) -> AgentExecutor:
    """
    Build a single domain agent with its own tools.

    domain_cfg:
    - name: str              -> e.g. "Medical KG Agent"
    - system_message: str    -> how this agent should behave
    - tool_configs: List[Dict[str, Any]] -> passed to build_dynamic_tools
    """
    tools = build_dynamic_tools(domain_cfg["tool_configs"], llm)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", domain_cfg["system_message"]),
            ("human", "{input}"),
            # Optional: if you want chat history:
            # ("human", "{chat_history}"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return executor


from langchain.tools import tool

def build_router_agent(
    agents_config: List[Dict[str, Any]],
    llm,
) -> AgentExecutor:
    """
    Build a top-level router agent over multiple domain agents.

    agents_config: List of:
    - name: str                -> "Medical KG Agent"
    - description: str         -> how/when to use this agent
    - system_message: str      -> passed to build_domain_agent
    - tool_configs: [...]      -> list for build_dynamic_tools
    """
    # 1) Build all domain agents
    domain_agents = {}
    agent_tools = []

    for cfg in agents_config:
        agent_name = cfg["name"]
        agent_desc = cfg["description"]

        executor = build_domain_agent(cfg, llm)
        domain_agents[agent_name] = executor

        # Wrap the agent as a tool
        @tool(agent_name)
        def domain_agent_tool(
            query: str,
            _executor=executor,
            _agent_name=agent_name,
            _agent_desc=agent_desc,
        ) -> str:
            """Dynamically generated domain agent tool."""
            # `query` is the user input routed to this domain agent
            result = _executor.invoke({"input": query})
            # AgentExecutor typically returns dict with "output"
            return result.get("output", str(result))

        domain_agent_tool.__doc__ = agent_desc
        domain_agent_tool.__name__ = agent_name.lower().replace(" ", "_")
        agent_tools.append(domain_agent_tool)

    # 2) Build router prompt
    router_system = """
    You are a router that selects the SINGLE best expert agent to answer the user's query.

    - Read the user's query.
    - Choose exactly ONE agent tool whose description best matches the query.
    - Call that agent tool with the user's query.
    - Return the agent's answer as the final answer.
    - Do NOT explain that you are routing; just answer naturally.
    """

    router_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", router_system),
            ("human", "{input}"),
        ]
    )

    # 3) Create router agent with the agent-tools
    router_llm = llm
    router_core_agent = create_tool_calling_agent(router_llm, agent_tools, router_prompt)
    router_executor = AgentExecutor(agent=router_core_agent, tools=agent_tools, verbose=True)

    return router_executor

# 1) Configure domain: Medical KG Agent
medical_agent_cfg = {
    "name": "Medical KG Agent",
    "description": "Use this agent for questions about diseases, symptoms, drugs, and clinical knowledge that is in the internal knowledge graphs.",
    "system_message": """
    You are a medical knowledge agent that uses internal knowledge graphs and tools.
    Always answer based on the tools (KGs, interaction graphs, etc.) and be concise and clinically sound.
    """,
    "tool_configs": [
        {
            "name": "Knowledge Graph Overview",
            "description": "Use this tool to answer generic questions about the medical knowledge graph.",
            "type": "kg_qa",
            "prompt_instructions": """
            You are an expert AI analyst working with a structured medical knowledge graph in JSON format.
            Extract concise answers based on entities and relationships in the graph.
            """,
            "json_string": medical_kg_json,
        },
        {
            "name": "Drug Interaction Checker",
            "description": "Use this tool to answer questions about drug-drug interactions using the interaction graph.",
            "type": "kg_qa",
            "prompt_instructions": """
            You are an expert on drug interactions. Use the JSON graph to check interactions between drugs
            and provide a short, clinically relevant explanation.
            """,
            "json_string": drug_interaction_kg_json,
        },
        {
            "name": "Disease Symptom Explorer",
            "description": "Use this tool to map diseases to their symptoms and related conditions.",
            "type": "kg_qa",
            "prompt_instructions": """
            You are an expert clinical knowledge explorer. Use the JSON graph to map diseases, symptoms,
            risk factors, and related conditions. Answer in simple, clear language.
            """,
            "json_string": disease_symptom_kg_json,
        },
    ],
}

# 2) Configure domain: External Data Agent (APIs + web portal)
external_data_agent_cfg = {
    "name": "External Data Agent",
    "description": "Use this agent when up-to-date data from external APIs or public health portals is needed.",
    "system_message": """
    You are an agent that fetches and summarizes up-to-date external information via APIs and web portals.
    Always clearly summarize external sources in simple language.
    """,
    "tool_configs": [
        {
            "name": "Clinical Guidelines API",
            "description": "Fetch clinical guideline summaries from the hospital's REST API.",
            "type": "rest_api",
            "method": "GET",
            "url": "https://api.hospital.com/guidelines/search",
            "query_param_name": "q",
            "default_params": {"limit": 5},
            "headers": {"Authorization": "Bearer <TOKEN>"},
        },
        {
            "name": "Public Health Web Portal Search",
            "description": "Search and extract relevant information from the public health web portal.",
            "type": "web_scrape",
            "url_template": "https://www.publichealth-portal.gov/search?q={query}",
            "css_selector": ".article-body",
            "prompt_instructions": """
            You are summarizing information from the official public health portal.
            Use only the extracted page content to answer the question in clear, non-technical language.
            """,
        },
    ],
}

# 3) Build router over both agents
agents_config = [medical_agent_cfg, external_data_agent_cfg]
router = build_router_agent(agents_config, llm)

# 4) Use the router in your app
user_query = "Does amoxicillin interact with warfarin?"
result = router.invoke({"input": user_query})
print(result["output"])
