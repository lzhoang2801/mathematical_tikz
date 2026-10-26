"""Experimental spatial interface, sharing the native drawing task contract."""
from agent.prompts.problem_tikz import problem_tikz_messages

SPATIAL_PROMPT_VERSION = 'spatial-construction-pilot:v1'
SPATIAL_VIEW_CONVENTION = '''For this spatial pilot, draw an unfilled diagram of the named closed convex solid. Its surface determines occlusion: visible boundary portions are solid, hidden portions are dashed. Classify section edges by their containing surface and interior segments by occlusion. Being auxiliary or derived is not a reason for dashes. Choose one consistent parallel view; either depth orientation is allowed, including a view with no hidden edges when geometrically valid. Keep visible named points distinct and avoid grazing/collapsed faces.'''


def spatial_task_messages(instruction: str) -> list[dict]:
    messages = problem_tikz_messages(instruction)
    messages[0]['content'] += '\n\n' + SPATIAL_VIEW_CONVENTION
    return messages
SPATIAL_INSTRUCTION = '''Experimental submission interface: submit a complete SpatialConstruction to render_spatial_construction. Work in one XYZ frame. Select independent parameters and derive every constrained point with named lerp, translate or intersect operations. Intersect requires truly intersecting 3D supporting lines, not skew lines that happen to cross on screen. Never assume a proof goal.

Supply cyclic boundary faces of one closed convex solid. The tool validates planarity, convexity and closure, draws its edges, chooses a parallel camera from a fixed candidate set, and projects every point together. Supply requested extra segments on or inside the solid; section edges and internal diagonals are different geometric roles. Visibility comes from actual front-face membership and occlusion, never from being a spatial problem, an auxiliary or a reflected point. Faces are unfilled; the closed solid's surface defines visibility. The current interface does not support transparent/open solids, nonconvex objects, curves or external segments.

Add equality ticks only when justified by the instruction, with matching group numbers; each class is checked in XYZ. Ticks decorate existing carriers without redrawing them. Internal point names use letters/digits; visible label text supports primes and subscripts, such as A' and A_1. position=auto chooses an angular gap among incident projected lines; you may choose a native position explicitly if the image needs adjustment. This heuristic does not guarantee collision-free text.

The tool emits complete ordinary TikZ with named affine dependencies. Inspect the image and source requirements in a subsequent turn before completion, within the same call budget. It does not know the instruction or certify its fidelity. No raw-code escape hatch is available.'''


def spatial_construction_messages(instruction: str) -> list[dict]:
    messages = spatial_task_messages(instruction)
    messages[0]['content'] = messages[0]['content'].replace('Submit a complete tikzpicture to render_tikz.', 'Submit a complete spatial construction to render_spatial_construction.').replace('render_tikz', 'render_spatial_construction') + '\n\n' + SPATIAL_INSTRUCTION
    return messages
