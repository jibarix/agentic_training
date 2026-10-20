"""Chapter 1's three tools, pointed at this chapter's larger handbook.

Chapter 1's tools read the module-level HANDBOOK path on every call, so setting it once here is
enough. Import this module before Chapter 1's agent uses the tools.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ch01"))
import tools as ch01_tools                                   # noqa: E402

ch01_tools.HANDBOOK = HERE / "handbook"
TOOLS, TOOLS_V1 = ch01_tools.TOOLS, ch01_tools.TOOLS_V1
lookup, lookup_v1, ToolError = ch01_tools.lookup, ch01_tools.lookup_v1, ch01_tools.ToolError
