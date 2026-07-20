
from __future__ import annotations

import json
import random
import re

from .db import connect

TOTAL_TURNS = 15
ACT_LABELS = {
    1: "第一幕｜今天到底算不算正常報到",
    2: "第二幕｜這公司真的有問題",
    3: "第三幕｜怪功與人心都開始留下後果",
    4: "第四幕｜你要選哪一邊",
}

EMOTIONS = ("warmth", "anger", "anxiety", "curiosity", "amusement", "suspicion")
EMOTION_LABELS = {
    "warmth": "親近",
    "anger": "生氣",
    "anxiety": "焦慮",
    "curiosity": "好奇",
    "amusement": "覺得荒謬好笑",
    "suspicion": "懷疑",
}


def rows(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def row(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchone()


def act_for(turn: int) -> int:
    return 1 if turn <= 3 else 2 if turn <= 7 else 3 if turn <= 11 else 4


def rng(state):
    state["rng_seed"] = (state["rng_seed"] * 1103515245 + 12345) % (2**31)
    return random.Random(state["rng_seed"])


def clamp(value: int) -> int:
    return max(0, min(10, int(value)))


def profile_for(role_key: str):
    q = row("SELECT * FROM character_profiles_v4 WHERE role_key=?", (role_key,))
    return dict(q) if q else {}


def new_game(name="新人", seed=None, avoid_openings=None):
    rg = random.Random(seed)
    characters = [dict(x) for x in rows("SELECT * FROM characters")]
    core = [x for x in characters if x["is_core"]]
    support = [x for x in characters if not x["is_core"]]
    active = core + rg.sample(support, 6)
    secret = dict(rg.choice(rows("SELECT * FROM world_secrets")))

    identities = {}
    profiles = {}
    emotions = {}

    for char in active:
        role = char["role_key"]
        variants = rows(
            "SELECT variant_text FROM character_identity_variants WHERE role_key=?",
            (role,),
        )
        identities[role] = rg.choice(variants)["variant_text"] if variants else ""
        p = profile_for(role)
        profiles[role] = p
        bias = json.loads(p.get("emotion_bias_json", "{}") or "{}")
        emotions[role] = {e: clamp(bias.get(e, 0)) for e in EMOTIONS}

    state = {
        "player_name": name.strip() or "新人",
        "turn": 0,
        "secret_key": secret["secret_key"],
        "secret_title": secret["title"],
        "secret_description": secret["description"],
        "active_roles": [x["role_key"] for x in active],
        "active_characters": {x["role_key"]: x for x in active},
        "character_profiles": profiles,
        "identities": identities,
        "relationships": {x["role_key"]: 0 for x in active},
        "character_emotions": emotions,
        "emotion_history": [],
        "techniques": [],
        "technique_use_count": {},
        "active_technique_effects": [],
        "pending_technique_events": [],
        "technique_countered": [],
        "used_combos": [],
        "ending_votes": {
            "reform": 0,
            "expose": 0,
            "escape": 0,
            "takeover": 0,
            "absurd": 0,
            "join": 0,
        },
        "clues": [],
        "secret_progress": 0,
        "flags": [],
        "used_event_ids": [],
        "used_families": [],
        "used_choice_texts": [],
        "used_dialogue_texts": [],
        "used_dialogue_variant_ids": [],
        "recent_focus": [],
        "current_scene": None,
        "last_result": "",
        "last_gain": "",
        "dialogue_queue": [],
        "dialogue_pending": False,
        "ending_bias": "",
        "ending": None,
        "opening_avoid": list(avoid_openings or [])[-4:],
        "opening_family": "",
        "rng_seed": rg.randrange(1, 10**9),
    }
    ensure_scene(state)
    return state


def resolve_focus(state, focus):
    if focus != "support":
        return focus
    fixed_core = {
        "guard", "rookie", "manager", "hr", "friend", "ceo",
        "finance", "legal", "it", "general", "courier", "cafe",
    }
    options = [x for x in state["active_roles"] if x not in fixed_core]
    return rng(state).choice(options)


def fresh(state, items):
    if not items:
        return ""
    used = set(state["used_dialogue_texts"])
    pool = [x for x in items if x not in used] or items
    picked = rng(state).choice(pool)
    state["used_dialogue_texts"].append(picked)
    state["used_dialogue_texts"] = state["used_dialogue_texts"][-220:]
    return picked


def tech_profile(tech_key):
    return row(
        "SELECT * FROM technique_effect_profiles_v3 WHERE tech_key=?",
        (tech_key,),
    )


def tech_name(tech_key):
    q = row("SELECT name FROM techniques WHERE tech_key=?", (tech_key,))
    return q["name"] if q else tech_key


def dominant_emotion(state, role):
    emotions = state["character_emotions"].get(role, {})
    if not emotions:
        return "curiosity", 0
    return max(emotions.items(), key=lambda x: x[1])


def emotion_summary(state, role):
    emotion, value = dominant_emotion(state, role)
    if value <= 1:
        return "情緒平穩"
    return f"{EMOTION_LABELS[emotion]} {value}/10"


def update_emotions(state, role, option):
    emotions = state["character_emotions"].setdefault(
        role, {e: 0 for e in EMOTIONS}
    )
    action = option.get("action_kind", "observe")
    deltas = {
        "probe": {"curiosity": 2, "suspicion": 1, "anxiety": 1},
        "direct": {"anger": 2, "suspicion": 1},
        "observe": {"curiosity": 1, "suspicion": 1},
        "public": {"anxiety": 2, "anger": 1, "suspicion": 1},
        "reform": {"curiosity": 1, "warmth": 1, "anxiety": 1},
        "conflict": {"anger": 3, "anxiety": 2, "suspicion": 1},
        "technique": {"amusement": 2, "curiosity": 2, "anxiety": 1},
        "absurd": {"amusement": 3, "curiosity": 1},
        "appease": {"anger": -3, "anxiety": -2, "warmth": 2},
        "confide": {"warmth": 3, "suspicion": -2, "anxiety": -1},
        "bait": {"curiosity": 3, "suspicion": 1},
        "joke": {"amusement": 3, "anger": -1, "warmth": 1},
        "reassure": {"anxiety": -3, "warmth": 2},
        "feint": {"suspicion": 2, "curiosity": 2},
    }.get(action, {"curiosity": 1}).copy()

    relationship_delta = int(option.get("relationship_delta", 0))
    if relationship_delta > 0:
        deltas["warmth"] = deltas.get("warmth", 0) + relationship_delta
    elif relationship_delta < 0:
        deltas["anger"] = deltas.get("anger", 0) + abs(relationship_delta)
        deltas["suspicion"] = deltas.get("suspicion", 0) + 1

    changes = {}
    for key, delta in deltas.items():
        before = emotions.get(key, 0)
        after = clamp(before + delta)
        emotions[key] = after
        if after != before:
            changes[key] = after - before

    # Public, conflict, technique and absurd actions also influence witnesses.
    if action in ("public", "conflict", "technique", "absurd"):
        others = [r for r in state["active_roles"] if r != role]
        for witness in rng(state).sample(others, min(2, len(others))):
            key = "anxiety" if action in ("public", "conflict") else "amusement"
            current = state["character_emotions"][witness].get(key, 0)
            state["character_emotions"][witness][key] = clamp(current + 1)

    state["emotion_history"].append({
        "turn": state["turn"],
        "role": role,
        "changes": changes,
        "action": action,
    })


def emotion_reaction_line(state, role):
    emotion, value = dominant_emotion(state, role)
    if value < 3:
        return ""
    intensity = 3 if value >= 8 else 2 if value >= 5 else 1
    candidates = [
        x["line_text"] for x in rows(
            """SELECT line_text FROM character_emotion_lines_v4
               WHERE role_key=? AND emotion=? AND intensity=?
               ORDER BY RANDOM() LIMIT 12""",
            (role, emotion, intensity),
        )
    ]
    return fresh(state, candidates)


def emotion_option(state, scene):
    role = scene["focus_role"]
    emotion, value = dominant_emotion(state, role)
    if value < 5:
        return None

    npc = state["active_characters"].get(role, {}).get("short_name", "對方")
    specs = {
        "anger": (
            "先不追問，承認剛才踩到他的雷，讓他把火氣說完",
            "appease",
            f"你先讓{npc}把火氣說完，至少他不再只想把你轟出去。",
            2,
        ),
        "anxiety": (
            "告訴他：真的出事你不會把責任全推給他",
            "reassure",
            f"你明確告訴{npc}不會讓他一個人背鍋，他的肩膀明顯鬆了一點。",
            2,
        ),
        "curiosity": (
            "故意只透露半個答案，引他主動把剩下秘密補完",
            "bait",
            f"你只說一半，{npc}果然忍不住追問，甚至自己補出原本不打算說的細節。",
            1,
        ),
        "amusement": (
            "順著他的笑點，把荒謬再推一步，看他會不會同流合污",
            "joke",
            f"你把笑話接到底，{npc}竟真的開始替你出主意。",
            2,
        ),
        "suspicion": (
            "故意說一半真話一半廢話，看他對哪句反應最大",
            "feint",
            f"你丟出真假混合說法，{npc}只對其中一個細節立刻反應。",
            0,
        ),
        "warmth": (
            "私下請他幫你一次，不講大道理，只說你真的需要他",
            "confide",
            f"你直接向{npc}求助，他沒有立刻答應，但最後站到了你旁邊。",
            3,
        ),
    }
    label, action, outcome, relationship_delta = specs[emotion]
    return {
        "id": f"emotion_{role}_{emotion}_{state['turn']}",
        "label": "🎭 " + label,
        "option_label": "🎭 " + label,
        "action_kind": action,
        "outcome_text": outcome,
        "relationship_delta": relationship_delta,
        "clue_gain": 1 if emotion in ("curiosity", "suspicion") else 0,
        "learn_tag": "",
        "learn_chance": 0.0,
        "flag": f"emotion_unlock_{role}_{emotion}",
        "ending_bias": (
            "expose" if emotion in ("curiosity", "suspicion")
            else "reform" if emotion in ("anger", "anxiety", "warmth")
            else "absurd"
        ),
        "emotion_special": True,
        "emotion_key": emotion,
    }


def pending_scene(state):
    due = [
        x for x in state["pending_technique_events"]
        if x["due_turn"] <= state["turn"]
    ]
    if not due:
        return None
    item = sorted(due, key=lambda x: x["due_turn"])[0]
    state["pending_technique_events"].remove(item)

    role = item.get("focus_role") or rng(state).choice(state["active_roles"])
    tech = item.get("tech_name", "怪功")

    return {
        "id": -500000 - state["turn"],
        "family": item["family"],
        "act": act_for(state["turn"]),
        "category": "technique",
        "focus_role": role,
        "title": item["title"],
        "body": item["body"],
        "extra_line": f"這不是提示，而是《{tech}》真的在後續世界留下痕跡。",
        "tags": ["technique", "social", "secret"],
        "is_special": True,
        "special_choices": [
            {
                "id": "tc0",
                "label": f"承認《{tech}》是你搞出來的，後果也算自己頭上",
                "action_kind": "technique",
                "outcome_text": f"你承認《{tech}》就是你用的。",
                "relationship_delta": 1,
                "clue_gain": 0,
                "learn_tag": "",
                "learn_chance": 0.0,
                "flag": "owned_consequence",
                "ending_bias": item.get("ending_bias", ""),
            },
            {
                "id": "tc1",
                "label": f"找人研究如何破解《{tech}》",
                "action_kind": "reform",
                "outcome_text": f"你開始替《{tech}》建立使用規則。",
                "relationship_delta": 0,
                "clue_gain": 0,
                "learn_tag": "",
                "learn_chance": 0.0,
                "flag": "counter_research",
                "ending_bias": "reform",
            },
            {
                "id": "tc2",
                "label": f"趁大家怕《{tech}》，把混亂拿去逼真相",
                "action_kind": "probe",
                "outcome_text": f"你把《{tech}》的餘波當掩護。",
                "relationship_delta": 0,
                "clue_gain": 1,
                "learn_tag": "",
                "learn_chance": 0.0,
                "flag": "weaponized_consequence",
                "ending_bias": "expose",
            },
        ],
    }


def add_ripple(state, scene):
    state["active_technique_effects"] = [
        x for x in state["active_technique_effects"]
        if x["expires_turn"] >= state["turn"]
    ]
    if not state["active_technique_effects"]:
        return

    item = rng(state).choice(state["active_technique_effects"])
    profile = tech_profile(item["tech_key"])
    if not profile:
        return

    text = profile["persistent_effect"]
    if state["technique_use_count"].get(item["tech_key"], 0) >= 2:
        text += " " + profile["countermeasure"]

    scene["extra_line"] = (
        scene.get("extra_line", "")
        + f"\n\n【功法餘波｜《{item['tech_name']}》】{text}"
    )


def pick_opening_event(state):
    families = [
        x["family"] for x in rows(
            "SELECT DISTINCT family FROM events WHERE act=1 AND is_finale=0"
        )
    ]
    avoid = set(state.get("opening_avoid", []))
    allowed = [f for f in families if f not in avoid] or families
    family = rng(state).choice(allowed)

    event_rows = rows(
        "SELECT * FROM events WHERE act=1 AND is_finale=0 AND family=?",
        (family,),
    )
    scene = dict(rng(state).choice(event_rows))
    state["opening_family"] = family
    return scene


def ensure_scene(state):
    if state.get("ending"):
        return {}
    if state.get("current_scene"):
        return state["current_scene"]

    # The last decision is always the true finale, never a delayed side effect.
    if state["turn"] < TOTAL_TURNS - 1:
        pending = pending_scene(state)
        if pending:
            state["current_scene"] = pending
            return pending

    act = act_for(state["turn"])

    if state["turn"] == 0:
        scene = pick_opening_event(state)
        scene["focus_role"] = resolve_focus(state, scene["focus_role"])
    else:
        if state["turn"] == TOTAL_TURNS - 1:
            source = rows(
                """SELECT * FROM events
                   WHERE is_finale=1 AND secret_key=?
                   ORDER BY RANDOM() LIMIT 60""",
                (state["secret_key"],),
            )
        else:
            source = rows(
                """SELECT * FROM events
                   WHERE is_finale=0 AND act=?
                   ORDER BY RANDOM() LIMIT 240""",
                (act,),
            )

        candidates = []
        for q in source:
            item = dict(q)
            if item["id"] in state["used_event_ids"]:
                continue
            if item["family"] in state["used_families"]:
                continue
            focus = resolve_focus(state, item["focus_role"])
            if state["recent_focus"] and focus == state["recent_focus"][-1]:
                continue
            item["focus_role"] = focus
            candidates.append(item)

        if not candidates:
            for q in source:
                item = dict(q)
                if item["id"] in state["used_event_ids"]:
                    continue
                if item["family"] in state["used_families"]:
                    continue
                item["focus_role"] = resolve_focus(state, item["focus_role"])
                candidates.append(item)

        if not candidates:
            raise RuntimeError("找不到可用事件")

        scene = rng(state).choice(candidates)

    scene["tags"] = (
        json.loads(scene["tags_json"])
        if "tags_json" in scene
        else scene.get("tags", [])
    )
    scene["is_special"] = False
    add_ripple(state, scene)

    state["current_scene"] = scene
    state["used_event_ids"].append(scene["id"])
    state["used_families"].append(scene["family"])
    state["recent_focus"] = (state["recent_focus"] + [scene["focus_role"]])[-3:]
    return scene


def tech_options(state, scene):
    possible = []
    scene_tags = set(scene.get("tags", []))

    for tech_key in state["techniques"]:
        technique = row(
            "SELECT * FROM techniques WHERE tech_key=?",
            (tech_key,),
        )
        if not technique:
            continue

        matching_tags = scene_tags & set(
            json.loads(technique["trigger_tags_json"])
        )
        for tag in matching_tags:
            for use in rows(
                """SELECT * FROM technique_uses
                   WHERE tech_key=? AND scene_tag=?
                   ORDER BY RANDOM() LIMIT 8""",
                (tech_key, tag),
            ):
                option = dict(use)
                if option["option_label"] in state["used_choice_texts"]:
                    continue
                option.update({
                    "is_technique": True,
                    "action_kind": "technique",
                    "relationship_delta": 1,
                    "clue_gain": 0,
                    "learn_tag": "",
                    "learn_chance": 0.0,
                    "flag": "used_" + tech_key,
                    "ending_bias": "",
                    "tech_name": technique["name"],
                    "scene_tag": tag,
                })
                possible.append(option)

    return possible


def combo_option(state):
    owned = set(state["techniques"])
    candidates = []

    for q in rows("SELECT * FROM technique_combo_effects_v3"):
        combo = dict(q)
        if combo["combo_key"] in state["used_combos"]:
            continue
        if combo["tech_a"] in owned and combo["tech_b"] in owned:
            candidates.append(combo)

    if not candidates:
        return None

    combo = rng(state).choice(candidates)
    return {
        "id": "combo_" + combo["combo_key"],
        "label": combo["option_label"],
        "option_label": combo["option_label"],
        "action_kind": "technique",
        "outcome_text": combo["immediate_effect"],
        "relationship_delta": 2,
        "clue_gain": 0,
        "learn_tag": "",
        "learn_chance": 0.0,
        "flag": "combo_" + combo["combo_key"],
        "ending_bias": combo["ending_bias"],
        "is_combo": True,
        "combo_key": combo["combo_key"],
        "combo_name": combo["combo_name"],
        "delayed_title": combo["delayed_title"],
        "delayed_body": combo["delayed_body"],
    }


def options_for_scene(state):
    scene = ensure_scene(state)
    if scene.get("is_special"):
        return scene["special_choices"]

    base = [
        dict(x) for x in rows(
            "SELECT * FROM choices WHERE event_id=? ORDER BY sort_order",
            (scene["id"],),
        )
        if x["label"] not in state["used_choice_texts"]
    ]

    emotion_special = emotion_option(state, scene)
    combo = combo_option(state)
    techniques = tech_options(state, scene)
    technique_special = None

    if combo and rng(state).random() < 0.45:
        technique_special = combo
    elif techniques:
        min_uses = min(
            state["technique_use_count"].get(x["tech_key"], 0)
            for x in techniques
        )
        low_use = [
            x for x in techniques
            if state["technique_use_count"].get(x["tech_key"], 0) == min_uses
        ]
        technique_special = rng(state).choice(low_use)
    elif combo:
        technique_special = combo

    # Once emotion crosses threshold, it is guaranteed to affect the option list.
    if emotion_special and technique_special:
        return (base[:2] + [emotion_special, technique_special])[:4]
    if emotion_special:
        return (base[:3] + [emotion_special])[:4]
    if technique_special:
        return (base[:3] + [technique_special])[:4]
    return base[:4]


def learn(state, tag, force=False):
    if not tag:
        return None

    candidates = []
    for q in rows("SELECT * FROM techniques"):
        technique = dict(q)
        if technique["tech_key"] in state["techniques"]:
            continue
        if tag in json.loads(technique["trigger_tags_json"]):
            candidates.append(technique)

    if not candidates:
        return None

    if not force and rng(state).random() > 0.65:
        return None

    technique = rng(state).choice(candidates)
    state["techniques"].append(technique["tech_key"])
    profile = tech_profile(technique["tech_key"])
    effect_type = profile["effect_type"] if profile else "奇葩"

    state["last_gain"] = (
        f"🥋 你意外領悟《{technique['name']}》：{technique['description']} "
        f"這門功法會留下「{effect_type}」型後果。"
    )
    return technique


def get_clue(state):
    stage = min(4, state["secret_progress"] + 1)
    q = row(
        """SELECT clue_text FROM secret_clues
           WHERE secret_key=? AND stage=?""",
        (state["secret_key"], stage),
    )
    if q and q["clue_text"] not in state["clues"]:
        state["clues"].append(q["clue_text"])
        state["secret_progress"] = stage
        return q["clue_text"]
    return ""


def dialogue_variant(state, choice_id):
    variants = [
        dict(x) for x in rows(
            "SELECT * FROM choice_dialogue_variants_v4 WHERE choice_id=?",
            (choice_id,),
        )
    ]
    pool = [
        x for x in variants
        if x["id"] not in state["used_dialogue_variant_ids"]
    ] or variants
    if not pool:
        return None

    picked = rng(state).choice(pool)
    state["used_dialogue_variant_ids"].append(picked["id"])
    return picked


def dialogue_for(state, role, action, scene, option):
    npc = state["active_characters"].get(role, {}).get("short_name", "？？？")
    label = option.get("label", option.get("option_label", ""))

    output = [{
        "speaker": state["player_name"],
        "text": "「" + label + "」",
        "kind": "player",
    }]

    if option.get("is_combo"):
        output.append({
            "speaker": npc,
            "text": (
                f"「你一次把兩門怪功疊一起？"
                f"……《{option['combo_name']}》這名字誰取的？」"
            ),
            "kind": "npc",
        })

    elif option.get("is_technique"):
        reaction = fresh(
            state,
            [
                x["reaction_text"] for x in rows(
                    """SELECT reaction_text
                       FROM technique_role_reactions_v3
                       WHERE tech_key=? AND role_key=?
                       ORDER BY RANDOM() LIMIT 10""",
                    (option["tech_key"], role),
                )
            ],
        )
        if reaction:
            output.append({
                "speaker": npc,
                "text": "「" + reaction + "」" if not reaction.startswith("「") else reaction,
                "kind": "npc",
            })
        if state["technique_use_count"].get(option["tech_key"], 0) >= 1:
            output.append({
                "speaker": npc,
                "text": "「而且你不是第一次用了。現在大家已經開始研究怎麼破解。」",
                "kind": "npc",
            })

    elif option.get("emotion_special"):
        output.append({
            "speaker": npc,
            "text": (
                f"「……你看得出來我現在"
                f"{EMOTION_LABELS[option['emotion_key']]}？」"
            ),
            "kind": "npc",
        })

    else:
        choice_id = option.get("id")
        if isinstance(choice_id, int):
            variant = dialogue_variant(state, choice_id)
            if variant:
                verb = {
                    "probe": "追問",
                    "direct": "直接碰",
                    "observe": "盯著看",
                    "public": "公開",
                    "reform": "改掉",
                    "conflict": "硬闖",
                    "absurd": "把事情搞得更荒謬",
                }.get(action, "處理")

                template = fresh(
                    state,
                    [
                        x["template_text"] for x in rows(
                            """SELECT template_text
                               FROM role_response_templates_v3
                               WHERE role_key=?
                               ORDER BY RANDOM() LIMIT 40""",
                            (role,),
                        )
                    ],
                )
                if template:
                    output.append({
                        "speaker": npc,
                        "text": template.format(verb=verb, hook=variant["hook"]),
                        "kind": "npc",
                    })
                output.append({
                    "speaker": "旁白",
                    "text": variant["consequence"],
                    "kind": "narration",
                })

    # The accumulated emotion modifies the current response tone.
    emotional_line = emotion_reaction_line(state, role)
    if emotional_line and len(output) < 4:
        output.append({
            "speaker": npc,
            "text": emotional_line,
            "kind": "npc",
        })

    if len(output) < 4:
        voice = fresh(
            state,
            [
                x["voice_line"] for x in rows(
                    """SELECT voice_line FROM role_voice_lines_v3
                       WHERE role_key=?
                       ORDER BY RANDOM() LIMIT 50""",
                    (role,),
                )
            ],
        )
        if voice:
            output.append({
                "speaker": npc,
                "text": voice,
                "kind": "npc",
            })

    if len(output) == 1:
        output.append({
            "speaker": npc,
            "text": "「你這個選法不一定安全，但至少不會無聊。」",
            "kind": "npc",
        })

    return output[:4]


def schedule_effect(state, tech_key, name, role):
    profile = tech_profile(tech_key)
    if not profile:
        return

    state["active_technique_effects"].append({
        "tech_key": tech_key,
        "tech_name": name,
        "expires_turn": state["turn"] + int(profile["duration_turns"]),
    })

    followups = rows(
        """SELECT title,body FROM technique_effect_followups_v3
           WHERE tech_key=? ORDER BY RANDOM() LIMIT 3""",
        (tech_key,),
    )
    if followups:
        followup = rng(state).choice(followups)
        due = min(
            TOTAL_TURNS - 2,
            state["turn"] + rng(state).randint(1, 3),
        )
        if due > state["turn"]:
            state["pending_technique_events"].append({
                "due_turn": due,
                "tech_key": tech_key,
                "tech_name": name,
                "focus_role": role,
                "title": followup["title"],
                "body": followup["body"],
                "ending_bias": profile["ending_bias"],
                "family": "tech_consequence_" + tech_key,
            })

    state["ending_votes"][profile["ending_bias"]] = (
        state["ending_votes"].get(profile["ending_bias"], 0) + 1
    )


def apply_technique(state, scene, option):
    tech_key = option["tech_key"]
    name = option["tech_name"]
    profile = tech_profile(tech_key)
    previous = state["technique_use_count"].get(tech_key, 0)
    state["technique_use_count"][tech_key] = previous + 1
    result = []

    if profile:
        result.append("🥋 功法實際影響：" + profile["immediate_effect"])

        if int(profile["clue_bonus"]) > 0 and scene["category"] != "finale":
            clue = get_clue(state)
            if clue:
                result.append(f"🔎 《{name}》額外逼出的線索：" + clue)

        if previous >= 1:
            result.append("⚠️ 對手已開始反制：" + profile["countermeasure"])
            if tech_key not in state["technique_countered"]:
                state["technique_countered"].append(tech_key)

        schedule_effect(
            state,
            tech_key,
            name,
            scene["focus_role"],
        )

    return result


def apply_combo(state, scene, option):
    if option["combo_key"] not in state["used_combos"]:
        state["used_combos"].append(option["combo_key"])

    state["ending_votes"][option["ending_bias"]] = (
        state["ending_votes"].get(option["ending_bias"], 0) + 2
    )

    due = min(TOTAL_TURNS - 2, state["turn"] + 2)
    if due > state["turn"]:
        state["pending_technique_events"].append({
            "due_turn": due,
            "tech_key": option["combo_key"],
            "tech_name": option["combo_name"],
            "focus_role": scene["focus_role"],
            "title": option["delayed_title"],
            "body": option["delayed_body"],
            "ending_bias": option["ending_bias"],
            "family": "combo_consequence_" + option["combo_key"],
        })

    return [
        "🔥 組合技成立：" + option["combo_name"],
        option["outcome_text"],
        "這個組合已被世界記住，之後會有專屬後果。",
    ]


def choose(state, option):
    scene = ensure_scene(state)
    role = scene["focus_role"]
    action = option.get("action_kind", "observe")
    label = option.get("label", option.get("option_label", ""))

    state["last_gain"] = ""

    # Update emotion BEFORE generating dialogue, so the reaction is immediate.
    update_emotions(state, role, option)
    state["dialogue_queue"] = dialogue_for(
        state, role, action, scene, option
    )
    state["dialogue_pending"] = True

    state["used_choice_texts"].append(label)
    state["used_choice_texts"] = state["used_choice_texts"][-280:]

    if role in state["relationships"]:
        state["relationships"][role] += int(
            option.get("relationship_delta", 0)
        )

    flag = option.get("flag", "")
    if flag and flag not in state["flags"]:
        state["flags"].append(flag)

    parts = []

    if option.get("is_combo"):
        parts.extend(apply_combo(state, scene, option))
    elif option.get("is_technique"):
        parts.append(option["outcome_text"])
        parts.extend(apply_technique(state, scene, option))
    else:
        parts.append(option["outcome_text"])

    if int(option.get("clue_gain", 0)) > 0:
        clue = get_clue(state)
        if clue:
            parts.append("🔎 新線索：" + clue)

    if not option.get("is_technique") and not option.get("is_combo"):
        force = state["turn"] >= 2 and not state["techniques"]
        if force or rng(state).random() < float(option.get("learn_chance", 0)):
            learn(
                state,
                option.get("learn_tag", ""),
                force,
            )

    ending_bias = option.get("ending_bias", "")
    if ending_bias:
        state["ending_bias"] = ending_bias
        state["ending_votes"][ending_bias] = (
            state["ending_votes"].get(ending_bias, 0) + 1
        )

    state["last_result"] = "\n\n".join(parts)
    state["turn"] += 1
    state["current_scene"] = None

    if state["turn"] >= TOTAL_TURNS:
        finish(state)
    else:
        ensure_scene(state)

    return state


def clean_word(name):
    text = re.sub(r"[《》]", "", name)
    for suffix in [
        "神功", "大法", "身法", "心法", "御劍術", "秘術",
        "劍術", "拳法", "掌法", "金鐘罩", "術", "訣",
        "掌", "劍", "刀", "拳", "步", "功", "陣",
    ]:
        text = text.replace(suffix, "")
    return text[:5] or "怪功"


def make_signature_technique(state, ending_bias):
    if not state["techniques"]:
        return {
            "name": "《新人試用期萬象自救訣》",
            "description": (
                "把裝傻、求生與準時下班融成一式；"
                "每次施展都能解決眼前一件事，"
                "並製造一件需要跨部門協調的新問題。"
            ),
        }

    ranked = sorted(
        state["techniques"],
        key=lambda k: state["technique_use_count"].get(k, 0),
        reverse=True,
    )[:3]
    names = [tech_name(k) for k in ranked]

    tail = {
        "reform": "流程逆天大法",
        "expose": "真相照妖神功",
        "escape": "準時下班無影訣",
        "takeover": "掌門也要報帳功",
        "absurd": "萬事皆可亂來訣",
        "join": "內門試用期飛升術",
    }.get(ending_bias, "社畜萬象歸一訣")

    fused_name = "《" + "・".join(clean_word(n) for n in names) + "・" + tail + "》"
    effect_types = [
        tech_profile(k)["effect_type"]
        for k in ranked
        if tech_profile(k)
    ]

    return {
        "name": fused_name,
        "description": (
            f"你把「{'＋'.join(names)}」揉成自己的路數。"
            f"此功專把{'、'.join(effect_types) or '荒謬因果'}塞進同一個辦公流程；"
            "每次解決一件事，保證再製造一件需要跨部門協調的新問題。"
        ),
    }


def make_achievements(state, ending_bias):
    achievements = []

    if len(state["techniques"]) >= 5:
        achievements.append((
            "功法收藏家",
            "十五回合內學會至少五門怪功，已不適合再自稱普通新人。",
        ))

    if state["used_combos"]:
        achievements.append((
            "融會貫通不是這樣用的",
            "成功把兩門不該放在一起的功法疊成組合技。",
        ))

    if len(state["technique_countered"]) >= 2:
        achievements.append((
            "全公司都在研究怎麼防你",
            "至少兩門功法被 NPC 正式列入反制名單。",
        ))

    if len(state["clues"]) >= 4:
        achievements.append((
            "新人不該知道這麼多",
            "核心秘密四階線索幾乎被你摸完整。",
        ))

    emotion_values = [
        (role, emotion, value)
        for role, emotion_map in state["character_emotions"].items()
        for emotion, value in emotion_map.items()
    ]

    if any(e == "warmth" and v >= 8 for _, e, v in emotion_values):
        achievements.append((
            "把邪教同事聊成自己人",
            "至少一名角色對你的親近高到願意替你扛事。",
        ))

    if any(e == "anger" and v >= 8 for _, e, v in emotion_values):
        achievements.append((
            "一句話逼到走火入魔邊緣",
            "至少一名角色被你累積惹火到最高危險區。",
        ))

    if any(e == "curiosity" and v >= 8 for _, e, v in emotion_values):
        achievements.append((
            "全公司最不會裝不知道的人",
            "你把某人的好奇心養到他自己主動查秘密。",
        ))

    ending_achievement = {
        "reform": (
            "邪教流程改善委員",
            "你逼百年門規開始填表、留紀錄、算工時。",
        ),
        "expose": (
            "公司機密的天敵",
            "你把最怕見光的東西一路推到快公開。",
        ),
        "escape": (
            "準時下班才是真正神功",
            "你把離開從逃跑練成戰略。",
        ),
        "takeover": (
            "還沒過試用期就想管整間公司",
            "你的選擇已經膨脹到治理層級。",
        ),
        "absurd": (
            "十五回合沒有一天正常",
            "你證明正常本身才是這家公司最稀有的事件。",
        ),
        "join": (
            "邪派新人自主創業",
            "你留下來，但拒絕照任何現成門規長大。",
        ),
    }
    achievements.append(
        ending_achievement.get(
            ending_bias,
            ending_achievement["absurd"],
        )
    )

    if len(achievements) < 3:
        achievements.append((
            "試用期生還者",
            "十五個主要決策後仍保有名字、員工證與基本自我認知。",
        ))

    if len(achievements) < 3:
        achievements.append((
            "奇葩功法創始人",
            "最後沒有照抄任何門派，而是把怪招煉成自己的東西。",
        ))

    return [
        {"title": title, "description": description}
        for title, description in achievements[:6]
    ]


def make_epilogue(state, signature, ending_bias):
    high_emotions = []

    for role, emotion_map in state["character_emotions"].items():
        emotion, value = max(emotion_map.items(), key=lambda x: x[1])
        if value >= 7:
            high_emotions.append((role, emotion, value))

    relation_note = ""
    if high_emotions:
        role, emotion, _ = high_emotions[0]
        name = state["active_characters"][role]["short_name"]
        relation_note = (
            f" 後來{name}每次看你準備起手式都會先看你一眼，"
            f"因為他對你留下最深的情緒是「{EMOTION_LABELS[emotion]}」。"
        )

    templates = {
        "reform": (
            f"三個月後，公司真的改了幾條百年門規。新人訓練新增一頁："
            f"『遇到{signature['name']}請先確認是否算工時。』"
            "你被傳成第一個靠流程改善逼退邪氣的人。"
        ),
        "expose": (
            f"半年後，江湖論壇流傳一段模糊影片：有人只用"
            f"{signature['name']}，就讓一場密室會議同時留下錄音、"
            "版本紀錄、報帳憑證和三份互相矛盾的公關聲明。"
        ),
        "escape": (
            f"你後來每換一家公司，都有人問履歷技能欄為什麼寫"
            f"{signature['name']}。你從不解釋，只在下午五點五十九分收東西；"
            "六點整，人不在座位，交接卻完整得可怕。"
        ),
        "takeover": (
            "你接手更多決策後，第一道命令是禁止沒有議程的會議，"
            "第二道命令是祖師遺訓必須有版本號。"
            f"至於{signature['name']}，被列為『掌門本人亦不得於季度結算前使用』。"
        ),
        "absurd": (
            f"沒人確定你最後站哪派，只知道城市裡開始有人模仿"
            f"{signature['name']}。一間公司因此縮短會議，一間開始替影印機買指定碳粉，"
            "另一家 HR 新增『轉世後復職』欄。"
        ),
        "join": (
            f"你留下後拒絕拜現成師父，硬靠{signature['name']}自成一派。"
            "門派特色不是制服，而是所有弟子必須會備份、看勞動法，"
            "而且不得下班後傳『在嗎』。"
        ),
    }

    return templates.get(ending_bias, templates["absurd"]) + relation_note


def finish(state):
    selected = state.get("ending_bias") or "absurd"

    if state["ending_votes"]:
        best_bias, best_score = max(
            state["ending_votes"].items(),
            key=lambda x: x[1],
        )
        if best_score >= 2:
            selected = best_bias

    q = row(
        """SELECT title,body FROM endings
           WHERE secret_key=? AND ending_bias=?""",
        (state["secret_key"], selected),
    )
    if not q:
        q = row(
            "SELECT title,body FROM endings WHERE secret_key=? LIMIT 1",
            (state["secret_key"],),
        )

    signature = make_signature_technique(state, selected)

    tech_summary = ""
    if state["technique_use_count"]:
        tech_key, use_count = max(
            state["technique_use_count"].items(),
            key=lambda x: x[1],
        )
        tech_summary = (
            f"\n\n你這局最常用《{tech_name(tech_key)}》（{use_count} 次），"
            "它確實改變了公司後續如何對付你。"
        )

    state["ending"] = {
        "title": q["title"],
        "body": q["body"] + tech_summary,
        "secret_title": state["secret_title"],
        "achievements": make_achievements(state, selected),
        "signature_technique": signature,
        "epilogue": make_epilogue(state, signature, selected),
    }


def relationship_label(value):
    if value >= 4:
        return "明顯站在你這邊"
    if value >= 2:
        return "開始信任你"
    if value <= -3:
        return "對你非常戒備"
    if value <= -1:
        return "有點不爽你"
    return "還在觀察你"


def active_character_cards(state):
    cards = []
    for role in state["active_roles"]:
        char = state["active_characters"][role]
        profile = state["character_profiles"].get(role, {})
        cards.append({
            "role_key": role,
            "name": char["short_name"],
            "job": char["job"],
            "relationship": relationship_label(
                state["relationships"].get(role, 0)
            ),
            "hook": char["comic_hook"],
            "personality": profile.get(
                "personality_core",
                char.get("personality", ""),
            ),
            "background": profile.get("background", ""),
            "desire": profile.get("desire", ""),
            "fear": profile.get("fear", ""),
            "soft_spot": profile.get("soft_spot", ""),
            "emotion": emotion_summary(state, role),
        })
    return cards


def owned_techniques(state):
    if not state["techniques"]:
        return []

    placeholders = ",".join("?" for _ in state["techniques"])
    techniques = [
        dict(x) for x in rows(
            f"SELECT * FROM techniques WHERE tech_key IN ({placeholders})",
            tuple(state["techniques"]),
        )
    ]

    for technique in techniques:
        profile = tech_profile(technique["tech_key"])
        technique["use_count"] = state["technique_use_count"].get(
            technique["tech_key"],
            0,
        )
        technique["persistent_effect"] = (
            profile["persistent_effect"] if profile else ""
        )
        technique["countered"] = (
            technique["tech_key"] in state["technique_countered"]
        )

    return techniques
