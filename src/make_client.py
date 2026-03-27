#!/usr/bin/env python3
"""
Make.com Automation Client
A professional Python SDK for deploying, managing, and orchestrating
Make.com automations via the REST API.
"""

import json
import time
from typing import Any, Dict, Iterator, List, Optional

import requests
from requests.exceptions import HTTPError, RequestException


class MakeClient:
    """
    Full-featured client for the Make.com REST API v2.

    Usage:
        client = MakeClient(
            api_token="your-token",
            zone="eu1.make.com",
            team_id=123
        )
        scenarios = client.list_scenarios()
    """

    def __init__(self, api_token: str, zone: str, team_id: int, org_id: Optional[int] = None):
        self.api_token = api_token
        self.zone = zone
        self.team_id = team_id
        self.org_id = org_id
        self.base_url = f"https://{zone}/api/v2"
        self.headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _request(self, method: str, path: str, max_retries: int = 3, timeout: int = 30, **kwargs) -> Dict:
        """Execute an API request with exponential-backoff retry on 429/5xx.

        Retry policy:
        - 429: sleep for ``Retry-After`` seconds (or ``2 ** attempt`` if absent), then retry.
        - 5xx / network errors: exponential backoff, up to ``max_retries`` attempts.
        - 4xx (except 429): raise immediately — these are caller errors, not transient failures.

        Args:
            timeout: Per-request timeout in seconds (default 30).
        """
        url = f"{self.base_url}{path}"
        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, timeout=timeout, **kwargs)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    delay = int(retry_after) if retry_after is not None else 2 ** attempt
                    time.sleep(delay)
                    continue
                resp.raise_for_status()  # raises HTTPError on 4xx and 5xx
                return resp.json() if resp.content else {}
            except HTTPError as exc:
                # 4xx errors are caller mistakes — raise immediately without retry.
                # 5xx errors are transient server failures — retry with backoff.
                if exc.response is not None and 400 <= exc.response.status_code < 500:
                    raise
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
            except RequestException:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Max retries exceeded for {url}")

    def paginate(self, path: str, result_key: str, page_size: int = 100, **params) -> Iterator[Dict]:
        """Yield all items from a paginated list endpoint."""
        offset = 0
        while True:
            page = self._request(
                "GET",
                path,
                params={**params, "pg[limit]": page_size, "pg[offset]": offset},
            )
            items = page.get(result_key, [])
            yield from items
            if len(items) < page_size:
                break
            offset += page_size

    # -------------------------------------------------------------------------
    # Scenarios
    # -------------------------------------------------------------------------

    def list_scenarios(self, folder_id: Optional[int] = None) -> List[Dict]:
        params = {"teamId": self.team_id}
        if folder_id:
            params["folderId"] = folder_id
        return self._request("GET", "/scenarios", params=params).get("scenarios", [])

    def get_scenario(self, scenario_id: int) -> Dict:
        return self._request("GET", f"/scenarios/{scenario_id}").get("scenario", {})

    def get_blueprint(self, scenario_id: int) -> Dict:
        return self._request("GET", f"/scenarios/{scenario_id}/blueprint").get("response", {})

    def create_scenario(
        self,
        blueprint: Dict,
        scheduling: Optional[Dict] = None,
        folder_id: Optional[int] = None,
    ) -> int:
        """Create a scenario from a blueprint dict. Returns the new scenario ID."""
        payload: Dict[str, Any] = {
            "blueprint": json.dumps(blueprint),
            "teamId": self.team_id,
            "scheduling": json.dumps(scheduling or {"type": "indefinitely", "interval": 900}),
        }
        if folder_id:
            payload["folderId"] = folder_id
        data = self._request("POST", "/scenarios", json=payload)
        return data["scenario"]["id"]

    def update_scenario(self, scenario_id: int, blueprint: Dict) -> Dict:
        payload = {"blueprint": json.dumps(blueprint)}
        return self._request("PATCH", f"/scenarios/{scenario_id}", json=payload)

    def activate_scenario(self, scenario_id: int) -> None:
        self._request("POST", f"/scenarios/{scenario_id}/start")

    def deactivate_scenario(self, scenario_id: int) -> None:
        self._request("POST", f"/scenarios/{scenario_id}/stop")

    def delete_scenario(self, scenario_id: int) -> None:
        self._request("DELETE", f"/scenarios/{scenario_id}")

    def run_scenario(
        self,
        scenario_id: int,
        data: Optional[Dict] = None,
        responsive: bool = True,
    ) -> Dict:
        """
        Execute a scenario on-demand.

        Args:
            scenario_id: Target scenario.
            data: Input data mapped to the scenario's defined inputs.
            responsive: If True, waits up to 40 s for completion.

        Returns:
            Execution result including executionId and status.
        """
        payload: Dict[str, Any] = {"responsive": responsive}
        if data:
            payload["data"] = data
        return self._request("POST", f"/scenarios/{scenario_id}/run", json=payload)

    def paginate_scenarios(self, folder_id: Optional[int] = None, page_size: int = 100) -> Iterator[Dict]:
        """Yield every scenario for the team, fetching pages as needed."""
        extra: Dict[str, Any] = {"teamId": self.team_id}
        if folder_id:
            extra["folderId"] = folder_id
        yield from self.paginate("/scenarios", "scenarios", page_size, **extra)

    def set_scenario_interface(self, scenario_id: int, inputs: List[Dict], outputs: List[Dict]) -> None:
        """Define inputs/outputs so the scenario can be used as an MCP tool or AI Agent tool."""
        payload = {"inputs": inputs, "outputs": outputs}
        self._request("PUT", f"/scenarios/{scenario_id}/inputs-outputs", json=payload)

    # -------------------------------------------------------------------------
    # Executions & Logs
    # -------------------------------------------------------------------------

    def list_executions(self, scenario_id: int, limit: int = 100) -> List[Dict]:
        params = {"scenarioId": scenario_id, "pg[limit]": limit}
        return self._request("GET", "/executions", params=params).get("executions", [])

    def get_execution(self, execution_id: str) -> Dict:
        return self._request("GET", f"/executions/{execution_id}").get("execution", {})

    def get_scenario_logs(self, scenario_id: int, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        params: Dict[str, Any] = {"limit": limit, "offset": 0}
        if status:
            params["status"] = status
        return self._request("GET", f"/scenarios/{scenario_id}/logs", params=params).get("logs", [])

    # -------------------------------------------------------------------------
    # Webhooks / Hooks
    # -------------------------------------------------------------------------

    def list_hooks(self) -> List[Dict]:
        return self._request("GET", "/hooks", params={"teamId": self.team_id}).get("hooks", [])

    def create_hook(self, name: str, include_method: bool = True, include_headers: bool = True) -> Dict:
        payload = {
            "teamId": self.team_id,
            "name": name,
            "typeName": "gateway-webhook",
            "method": include_method,
            "header": include_headers,
            "stringify": False,
        }
        return self._request("POST", "/hooks", json=payload)

    def delete_hook(self, hook_id: int) -> None:
        self._request("DELETE", f"/hooks/{hook_id}")

    # -------------------------------------------------------------------------
    # Data Structures
    # -------------------------------------------------------------------------

    def create_data_structure(self, name: str, spec: List[Dict], strict: bool = True) -> int:
        payload = {"teamId": self.team_id, "name": name, "strict": strict, "spec": spec}
        return self._request("POST", "/data-structures", json=payload)["dataStructure"]["id"]

    def list_data_structures(self) -> List[Dict]:
        return self._request("GET", "/data-structures", params={"teamId": self.team_id}).get(
            "dataStructures", []
        )

    # -------------------------------------------------------------------------
    # Data Stores
    # -------------------------------------------------------------------------

    def create_data_store(self, name: str, structure_id: int, max_size_mb: int = 100) -> int:
        payload = {
            "name": name,
            "teamId": self.team_id,
            "datastructureId": structure_id,
            "maxSizeMB": max_size_mb,
        }
        return self._request("POST", "/data-stores", json=payload)["dataStore"]["id"]

    def list_data_stores(self) -> List[Dict]:
        return self._request("GET", "/data-stores", params={"teamId": self.team_id}).get(
            "dataStores", []
        )

    def get_data_store(self, store_id: int) -> Dict:
        return self._request("GET", f"/data-stores/{store_id}").get("dataStore", {})

    def add_record(self, store_id: int, data: Dict, key: Optional[str] = None) -> Dict:
        payload: Dict[str, Any] = {"data": data}
        if key:
            payload["key"] = key
        return self._request("POST", f"/data-stores/{store_id}/data", json=payload)

    def list_records(self, store_id: int, limit: int = 100, offset: int = 0) -> List[Dict]:
        params = {"limit": limit, "offset": offset}
        return self._request("GET", f"/data-stores/{store_id}/data", params=params).get("records", [])

    def paginate_records(self, store_id: int, page_size: int = 100) -> Iterator[Dict]:
        """Yield every record in a data store, fetching pages as needed.

        Uses ``limit``/``offset`` query params (not ``pg[limit]``/``pg[offset]``)
        because the data-store records endpoint has a different pagination scheme
        from the scenario/scenario-list endpoints.
        """
        offset = 0
        while True:
            items = self.list_records(store_id, limit=page_size, offset=offset)
            yield from items
            if len(items) < page_size:
                break
            offset += page_size

    def update_record(self, store_id: int, key: str, data: Dict) -> Dict:
        payload = {"key": key, "data": data}
        return self._request("PATCH", f"/data-stores/{store_id}/data", json=payload)

    def replace_record(self, store_id: int, key: str, data: Dict) -> Dict:
        payload = {"key": key, "data": data}
        return self._request("PUT", f"/data-stores/{store_id}/data", json=payload)

    def delete_records(self, store_id: int, keys: List[str]) -> None:
        payload = {"keys": keys, "confirmed": True}
        self._request("DELETE", f"/data-stores/{store_id}/data", json=payload)

    # -------------------------------------------------------------------------
    # Connections
    # -------------------------------------------------------------------------

    def list_connections(self, connection_type: Optional[str] = None) -> List[Dict]:
        params: Dict[str, Any] = {"teamId": self.team_id}
        if connection_type:
            params["type[]"] = connection_type
        return self._request("GET", "/connections", params=params).get("connections", [])

    def verify_connection(self, connection_id: int) -> bool:
        result = self._request("POST", f"/connections/{connection_id}/verify")
        return result.get("verified", False)

    # -------------------------------------------------------------------------
    # Organizations & Teams
    # -------------------------------------------------------------------------

    def list_teams(self) -> List[Dict]:
        if not self.org_id:
            raise ValueError("org_id is required to list teams")
        return self._request("GET", "/teams", params={"organizationId": self.org_id}).get("teams", [])

    def get_team(self, team_id: int) -> Dict:
        return self._request("GET", f"/teams/{team_id}").get("team", {})

    def get_organization(self, org_id: int) -> Dict:
        return self._request("GET", f"/organizations/{org_id}").get("organization", {})

    # -------------------------------------------------------------------------
    # AI Agents (Beta)
    # -------------------------------------------------------------------------

    def create_agent(self, config: Dict) -> int:
        """
        Create an AI Agent.

        The config dict must include: name, systemPrompt, defaultModel,
        llmConfig, invocationConfig, scenarios, outputParserFormat.
        """
        data = self._request(
            "POST",
            f"/ai-agents/v1/agents",
            params={"teamId": self.team_id},
            json=config,
        )
        return data["agent"]["id"]

    def run_agent(self, agent_id: int, messages: List[Dict], thread_id: Optional[str] = None) -> Dict:
        payload: Dict[str, Any] = {"messages": messages}
        if thread_id:
            payload["threadId"] = thread_id
        return self._request(
            "POST",
            f"/ai-agents/v1/agents/{agent_id}/run",
            params={"teamId": self.team_id},
            json=payload,
        )

    # -------------------------------------------------------------------------
    # Folders
    # -------------------------------------------------------------------------

    def list_folders(self) -> List[Dict]:
        return self._request("GET", "/scenarios/folders", params={"teamId": self.team_id}).get(
            "folders", []
        )

    def create_folder(self, name: str) -> int:
        payload = {"teamId": self.team_id, "name": name}
        return self._request("POST", "/scenarios/folders", json=payload)["folder"]["id"]

    # -------------------------------------------------------------------------
    # Analytics & Consumption
    # -------------------------------------------------------------------------

    def get_consumption(self, scenario_id: int, time_from: str, time_to: str) -> Dict:
        params = {"timeFrom": time_from, "timeTo": time_to}
        return self._request("GET", f"/scenarios/{scenario_id}/consumptions", params=params)


class MakeDeployer:
    """
    High-level deployer for full-stack Make.com automation stacks.

    Combines client calls into reusable deployment workflows:
    - deploy_with_datastore(): scenario + typed data store (structure + store)
    - deploy_mcp_tool(): on-demand scenario with typed I/O for MCP exposure
    - deploy_ai_agent_stack(): standalone AI Agent with scenarios as tools
    - deploy_scenario_agent(): scenario-embedded agent (ai-local-agent module)
    """

    def __init__(self, client: MakeClient):
        self.client = client

    def deploy_with_datastore(
        self,
        blueprint: Dict,
        store_name: str,
        structure_spec: List[Dict],
    ) -> Dict[str, Any]:
        """
        Deploy a scenario backed by a typed data store.

        Returns:
            {
                "scenario_id": int,
                "structure_id": int,
                "store_id": int,
            }
        """
        print(f"[1/3] Creating data structure '{store_name}'...")
        structure_id = self.client.create_data_structure(store_name, structure_spec)

        print(f"[2/3] Creating data store...")
        store_id = self.client.create_data_store(store_name, structure_id)

        print(f"[3/3] Deploying scenario blueprint...")
        scenario_id = self.client.create_scenario(blueprint)

        return {
            "scenario_id": scenario_id,
            "structure_id": structure_id,
            "store_id": store_id,
        }

    def deploy_mcp_tool(
        self,
        blueprint: Dict,
        inputs: List[Dict],
        outputs: List[Dict],
        activate: bool = True,
    ) -> int:
        """
        Deploy a scenario as an MCP tool (on-demand + typed I/O).

        Returns the scenario ID.
        """
        scheduling = {"type": "on-demand"}
        scenario_id = self.client.create_scenario(blueprint, scheduling=scheduling)
        self.client.set_scenario_interface(scenario_id, inputs, outputs)
        if activate:
            self.client.activate_scenario(scenario_id)
        print(f"MCP tool deployed → scenario {scenario_id}")
        return scenario_id

    def deploy_ai_agent_stack(self, agent_config: Dict, activate_tools: bool = True) -> int:
        """
        Deploy a standalone AI Agent with its backing scenarios as tools.

        Each scenario listed in agent_config["scenarios"] must already exist
        and be active before calling this method.  The agent is created via the
        REST API (``POST /ai-agents/v1/agents``) — the Make MCP toolset has no
        equivalent endpoint.

        Args:
            agent_config: Full agent configuration dict (name, systemPrompt,
                          defaultModel, llmConfig, invocationConfig, scenarios, …).
            activate_tools: Reserved for future use; currently unused.

        Returns:
            The newly created agent ID.
        """
        agent_id = self.client.create_agent(agent_config)
        print(f"AI Agent deployed → agent {agent_id}")
        return agent_id

    def deploy_scenario_agent(
        self,
        system_prompt: str,
        tools: List[Dict],
        model: str = "large",
        reasoning_effort: str = "low",
        recursion_limit: int = 50,
        history_count: int = 10,
        output_type: str = "text",
        scheduling: Optional[Dict] = None,
    ) -> int:
        """
        Deploy a scenario using the ai-local-agent:RunLocalAIAgent module.

        This is the NEW Make AI Agent pattern — the LLM lives INSIDE the
        scenario as a single module and orchestrates all tools via LLM
        reasoning at runtime.  Unlike the old linear-chain pattern, the agent
        decides tool call order itself.

        Args:
            system_prompt: Agent instructions.
            tools: List of tool dicts, each with "name", "description", and
                   "flow" (a list of Make module objects).
            model: "large", "medium", or "small".
            reasoning_effort: "low" (only valid value currently).
            recursion_limit: Max LLM steps per run (default 50).
            history_count: Conversation turns to retain (default 10).
            output_type: "text" or "make-schema".
            scheduling: Scenario scheduling config (defaults to on-demand).

        Returns:
            Scenario ID.
        """
        blueprint = {
            "name": f"AI Agent — {system_prompt[:40]}...",
            "flow": [
                {
                    "id": 1,
                    "module": "ai-local-agent:RunLocalAIAgent",
                    "version": 0,
                    "tools": tools,
                    "mapper": {
                        "message": "{{1.input}}",
                        "files": [],
                        "timeout": "",
                        "threadId": "",
                        "outputType": output_type,
                        "modelConfig": {
                            "recursionLimit": recursion_limit,
                            "iterationsFromHistoryCount": str(history_count),  # API requires string, not int
                        },
                        "defaultModel": model,
                        "systemPrompt": system_prompt,
                        "reasoningEffort": reasoning_effort,
                    },
                    "parameters": {},
                    "metadata": {"designer": {"x": 0, "y": 0}},
                }
            ],
            "metadata": {
                "instant": False,
                "version": 1,
                "designer": {"orphans": []},
                "scenario": {"slots": None, "autoCommit": True},
            },
        }
        sched = scheduling or {"type": "on-demand"}
        scenario_id = self.client.create_scenario(blueprint, scheduling=sched)
        print(f"Scenario agent deployed → scenario {scenario_id}")
        return scenario_id
