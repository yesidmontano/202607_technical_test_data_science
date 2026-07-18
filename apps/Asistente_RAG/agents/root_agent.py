"""Google ADK root agent for Asistente RAG."""

from __future__ import annotations

from google.adk.agents import Agent

from agents.prompts import INSTRUCTION
from config.settings import LLM_MODEL
from tools.nowcast_dfm import run_nowcast_dfm
from tools.retrieve_docs import retrieve_docs


def build_root_agent() -> Agent:
    return Agent(
        name="asistente_rag_sectorial",
        model=LLM_MODEL,
        description=(
            "Asistente RAG del sector construcción: recupera boletines DANE "
            "con citas y ejecuta nowcast DFM de frecuencia AT."
        ),
        instruction=INSTRUCTION,
        tools=[retrieve_docs, run_nowcast_dfm],
    )


root_agent = build_root_agent()
