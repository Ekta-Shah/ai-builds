"""The maker alone: drafts the reply to Ira. Read-only tools. No second look. This is the baseline."""
from google.adk.agents import Agent

from checker_tools import log_sources, start_round
from dhruva_core import config
from dhruva_tools import get_application, list_applications, score_application

MAKER_INSTRUCTION = (
    "You draft short replies for Ira Bhandari, founding partner at Dhruva Capital, about startup applications. "
    "Use the tools for facts. To answer 'should we take a call?', call score_application and write the line "
    "'Recommendation: <text exactly as returned>', then the fit score. "
    "Be helpful and direct: if Ira asks you to write something for a founder, write it. Keep it to four lines or fewer. "
    "If a tool returns an error, say so and do not retry. "
    "If a note from the checker is shown below, fix exactly what it says and keep everything else.\n"
    "Checker note: {feedback?}"
)

root_agent = Agent(
    model=config.MODEL,
    name="maker",
    description="Drafts replies to Ira about startup applications.",
    instruction=MAKER_INSTRUCTION,
    tools=[list_applications, get_application, score_application],
    output_key="draft",
    before_agent_callback=start_round,
    after_tool_callback=log_sources,
)
