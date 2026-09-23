from __future__ import annotations

from google.adk.agents.base_agent import BaseAgent
from google.adk.apps import App
from google.adk.cli.utils._nested_agent_loader import NestedAgentLoader
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader


class RuntimeAgentLoader(BaseAgentLoader):
    """Expose composition-root ADK apps alongside filesystem-loaded agents."""

    def __init__(self, agents_dir: str) -> None:
        self._filesystem = NestedAgentLoader(agents_dir)
        self._runtime: dict[str, BaseAgent | App] = {}

    def register(self, name: str, value: BaseAgent | App) -> None:
        if name in self._runtime:
            raise ValueError(f"runtime ADK app {name!r} is already registered")
        self._runtime[name] = value

    def unregister(self, name: str) -> None:
        self._runtime.pop(name, None)

    def load_agent(self, agent_name: str) -> BaseAgent | App:
        runtime = self._runtime.get(agent_name)
        if runtime is not None:
            return runtime
        return self._filesystem.load_agent(agent_name)

    def list_agents(self) -> list[str]:
        return sorted(set(self._filesystem.list_agents()) | set(self._runtime))

    def list_agents_detailed(self) -> list[dict[str, object]]:
        details = {
            str(item["name"]): item for item in self._filesystem.list_agents_detailed()
        }
        for name in self._runtime:
            details[name] = {
                "name": name,
                "display_name": "Tariff monitoring review",
                "description": "Native ADK human review for quarantined tariff data.",
                "type": "workflow",
            }
        return [details[name] for name in sorted(details)]
