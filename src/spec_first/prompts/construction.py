"""Method override for the bounded planar construction pilot."""
from agent.prompts.problem_tikz import problem_tikz_messages

CONSTRUCTION_PROMPT_VERSION = "construction-pilot:v1"
CONSTRUCTION_INSTRUCTION = """Experimental submission interface: submit a complete Construction object to render_construction instead of writing raw TikZ. The tool deterministically emits a complete tikzpicture, preserving named dependent coordinates and the shared drawing conventions. Do not send TikZ or arbitrary code to this tool.

Use only the documented operations. List points in dependency order. Free coordinates are independent layout parameters; use lerp, project, reflect, intersect or rotate for constrained points. project/reflect operate on supporting lines; select and check segment/ray branches yourself. rotate preserves distance to its center. Do not assume a proof goal. The tool checks degeneracy and the truth of requested marks, but it does not know the instruction. You remain responsible for its mathematical and visible requirements.

Specify visible segments, circles through named points, right/equal angle marks and labels. Ticks and equal-angle groups denote equality classes. Label ray endpoints x/y or a line d with dot=false. Minor angle sectors are ordered by the emitter. All labels and geometry must fit; choose positions before rendering. Inspect the returned image in a subsequent turn, then complete or submit a corrected whole construction within the same budget. No free-form source escape hatch is available in this pilot."""


def construction_messages(instruction: str) -> list[dict]:
    messages = problem_tikz_messages(instruction)
    messages[0]["content"] = messages[0]["content"].replace(
        "Submit a complete tikzpicture to render_tikz.",
        "Submit a complete construction to render_construction.",
    ).replace("render_tikz", "render_construction") + "\n\n" + CONSTRUCTION_INSTRUCTION
    return messages
