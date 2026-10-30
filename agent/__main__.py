"""Work the claims queue: uv run -m agent, or uv run -m agent CLM-1001 for one claim."""

import sys

from agent.main import work

work(sys.argv[1:])
