
from game.engine import (
    new_game, ensure_scene, options_for_scene, choose, emotion_option
)

state = new_game("情緒測試", 123)
scene = ensure_scene(state)
role = scene["focus_role"]
before = dict(state["character_emotions"][role])

choose(state, options_for_scene(state)[0])
after = state["character_emotions"][role]
assert before != after

state["current_scene"] = None
scene = ensure_scene(state)
role = scene["focus_role"]
state["character_emotions"][role]["warmth"] = 9
option = emotion_option(state, scene)
assert option
assert option["emotion_special"]
assert "🎭" in option["label"]

visible_options = options_for_scene(state)
assert any(x.get("emotion_special") for x in visible_options)

print("V4.7 emotion system test passed")
