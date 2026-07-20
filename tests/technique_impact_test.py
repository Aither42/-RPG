
from game.engine import new_game, ensure_scene, options_for_scene, choose

state = new_game("功法測試", 7)
state["techniques"] = [
    "seen_silence", "excel_sword", "ppt_dragon",
    "meeting_soul", "coat_clone",
]

used_technique = False
used_combo = False
seen_ripple = False
seen_followup = False
count = 0

while not state.get("ending"):
    scene = ensure_scene(state)

    if "【功法餘波" in scene.get("extra_line", ""):
        seen_ripple = True
    if scene["family"].startswith(("tech_consequence_", "combo_consequence_")):
        seen_followup = True

    options = options_for_scene(state)
    pick = next((x for x in options if x.get("is_combo")), None)
    if pick:
        used_combo = True

    if pick is None:
        pick = next((x for x in options if x.get("is_technique")), None)
        if pick:
            used_technique = True

    if pick is None:
        pick = options[0]

    choose(state, pick)
    state["dialogue_pending"] = False
    count += 1
    assert count <= 20

assert state["turn"] == 15
assert state["ending"]
assert used_technique or used_combo
assert state["technique_use_count"] or state["used_combos"]
assert seen_ripple or seen_followup or state["used_combos"]

print(
    "V4.7 technique impact test passed:",
    used_technique, used_combo, seen_ripple, seen_followup,
)
