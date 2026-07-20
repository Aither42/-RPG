
from game.engine import new_game

openings = [new_game("測試", seed)["opening_family"] for seed in range(120)]
assert len(set(openings)) >= 15, len(set(openings))
assert len(set(openings)) > 1

first = new_game("A", 1)["opening_family"]
for seed in range(2, 20):
    assert new_game("B", seed, avoid_openings=[first])["opening_family"] != first

print("V4.7 opening randomness test passed:", len(set(openings)), "unique families")
