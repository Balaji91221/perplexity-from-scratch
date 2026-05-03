"""All system prompts. One file per prompt, flat layout.

Files (alphabetical):
  analyst.py       ANALYST_PROMPT              specialist persona
  coder.py         CODER_PROMPT                specialist persona
  computer.py      COMPUTER_SYSTEM_PROMPT      mode prompt (Computer Use)
  deep.py          DEEP_SYSTEM_PROMPT          mode prompt (Deep)
  planner.py       ORCHESTRATOR_PLANNER_PROMPT multi-agent: decompose query
  quick.py         SYSTEM_PROMPT               mode prompt (Quick)
  researcher.py    RESEARCHER_PROMPT           specialist persona
  synthesizer.py   ORCHESTRATOR_SYNTH_PROMPT   multi-agent: merge sub-answers

Every constant is re-exported from this package, so callers can keep saying
`from agents.prompts import RESEARCHER_PROMPT` and not care about the file layout.
"""

from .analyst import ANALYST_PROMPT
from .coder import CODER_PROMPT
from .computer import COMPUTER_SYSTEM_PROMPT
from .deep import DEEP_SYSTEM_PROMPT
from .planner import ORCHESTRATOR_PLANNER_PROMPT
from .quick import SYSTEM_PROMPT
from .researcher import RESEARCHER_PROMPT
from .synthesizer import ORCHESTRATOR_SYNTH_PROMPT

__all__ = [
    "SYSTEM_PROMPT",
    "DEEP_SYSTEM_PROMPT",
    "COMPUTER_SYSTEM_PROMPT",
    "RESEARCHER_PROMPT",
    "CODER_PROMPT",
    "ANALYST_PROMPT",
    "ORCHESTRATOR_PLANNER_PROMPT",
    "ORCHESTRATOR_SYNTH_PROMPT",
]
