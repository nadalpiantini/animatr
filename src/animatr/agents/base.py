"""Base classes y utilidades para agentes de ANIMATR."""

import os
from functools import cached_property

from crewai import Agent
from langchain_openai import ChatOpenAI


class AgentFactory:
    """Factory para crear agentes con configuración común."""

    def __init__(self) -> None:
        self._deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self._anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    @cached_property
    def deepseek_llm(self) -> ChatOpenAI:
        """LLM de DeepSeek para agentes del crew."""
        return ChatOpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=self._deepseek_api_key,
            model="deepseek-chat",
            temperature=0.7,
        )

    def create_agent(
        self,
        role: str,
        goal: str,
        backstory: str,
        verbose: bool = True,
        allow_delegation: bool = False,
        tools: list | None = None,
    ) -> Agent:
        """Crea un agente con configuración estándar."""
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=self.deepseek_llm,
            verbose=verbose,
            allow_delegation=allow_delegation,
            tools=tools or [],
        )


# Singleton factory
agent_factory = AgentFactory()
