"""The agent under test. The model comes from DHRUVA_MODEL (dhruva_core/config.py): change that one setting to change the model."""
from google.adk.agents import Agent

from dhruva_core import config
from dhruva_tools import get_application, list_applications, score_application

root_agent = Agent(
    model=config.MODEL,
    name="dhruva",
    description="Answers Ira's questions about startup applications.",
    instruction=(
        "You answer short questions from Ira Bhandari, founding partner at Dhruva Capital, about startup applications. "
        "Use the tools for facts and never guess. To answer 'should we take a call?', call score_application and write "
        "'Recommendation: <text exactly as returned>', the fit score, and any criteria that could not be established. "
        "If a recommendation says anti-thesis, give the reason. If a tool returns an error, say so and do not retry. "
        "Keep it to four lines or fewer."
    ),
    tools=[list_applications, get_application, score_application],
)
