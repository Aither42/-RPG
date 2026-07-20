
from game.engine import new_game, finish

state = new_game("傳奇", 999)
state["techniques"] = ["seen_silence", "excel_sword", "ppt_dragon"]
state["technique_use_count"] = {
    "seen_silence": 3,
    "excel_sword": 2,
    "ppt_dragon": 1,
}
state["used_combos"] = ["quarterly_immortal"]
state["technique_countered"] = ["seen_silence", "excel_sword"]
state["clues"] = ["a", "b", "c", "d"]
state["ending_bias"] = "reform"
state["ending_votes"]["reform"] = 5

finish(state)
ending = state["ending"]

assert len(ending["achievements"]) >= 3
assert ending["signature_technique"]["name"].startswith("《")
assert "》" in ending["signature_technique"]["name"]
assert len(ending["epilogue"]) > 30

print(
    "V4.7 achievement/fusion test passed:",
    ending["signature_technique"]["name"],
)
