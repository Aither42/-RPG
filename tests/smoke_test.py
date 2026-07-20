
from game.engine import new_game, options_for_scene, choose

for seed in range(40):
    state = new_game("測試", seed)
    count = 0
    while not state.get("ending"):
        options = options_for_scene(state)
        assert options
        assert 2 <= len(options) <= 4
        choose(state, options[seed % len(options)])
        state["dialogue_pending"] = False
        count += 1
        assert count <= 20

    assert state["turn"] == 15
    assert state["ending"]
    assert state["ending"]["achievements"]
    assert state["ending"]["signature_technique"]["name"]
    assert state["ending"]["epilogue"]

print("V4.7 smoke test passed: 40 runs")
