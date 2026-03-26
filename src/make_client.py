#!/usr/bin/env python3
"""
Make.com Automation Client
A professional Python SDK for deploying, managing, and orchestrating
Make.com automations via the REST API.
"""

import json
import time
from typing import Any, Dict, List, Optional

import requests
from requests.exceptions import RequestException


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

    def _request(self, method: str, path: str, max_retries: int = 3, **kwargs) -> Dict:
        """Execute an API request with exponential-backoff retry on 429/5xx."""
        url = f"{self.base_url}{path}"
        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except RequestException as exc:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Max retries exceeded for {url}")

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
    - deploy_with_datastore(): webhook → scenario + data store
    - deploy_ai_agent_stack(): full AI Agent with tools + scenarios
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
                "webhook": dict | None
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
