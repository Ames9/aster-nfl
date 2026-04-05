"""
既存の day_N.json の criteria が一意に選手を特定できるかチェックする。
複合型ヒント（"Draft Class: 2017 Round 5" など）にも対応。
"""
import json, re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from generate_puzzles import (
    load_nflverse_players, load_nflverse_seasonal_rosters, load_nflverse_draft_picks,
    load_awards, players_matching,
    ROSTER_YEARS, MIN_SEASONS, canonical, TEAM_FULL_NAMES,
)
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# チェック対象 day 番号（コマンドライン引数があればそれを使う）
import sys as _sys
if len(_sys.argv) > 1:
    TARGET_DAYS = [int(x) for x in _sys.argv[1:]]
else:
    TARGET_DAYS = list(range(1, 62))

# ---- フルネーム → 略称 逆引き ----
FULL_TO_ABBR = {v: k for k, v in TEAM_FULL_NAMES.items()}


def hint_to_criteria(hint: str, hint_players: list, rosters: pd.DataFrame) -> list:
    """
    hint 文字列を criterion dict のリストに変換する。
    複合型（AND 条件）は複数要素を返す。
    players_matching() はリスト各要素の交集合でマッチング。
    """
    h = hint.strip()

    # ----------------------------------------------------------------
    # 複合型: "Draft Class: 2017 Round 5"（カンマあり・なし両対応）
    # ----------------------------------------------------------------
    m = re.match(r"Draft Class:\s*(\d{4})[,\s]+Round\s+(\d+)$", h)
    if m:
        yr, rd = int(m.group(1)), int(m.group(2))
        return [{"type": "draft_year_round", "label": h, "value": {"year": yr, "round": rd}}]

    # UDFA
    if re.search(r"UDFA|[Uu]ndrafted", h):
        return [{"type": "udfa", "label": h, "value": None}]

    # 複合型: "Drafted by Dallas Cowboys, 2014" / "2014, Drafted by Chiefs"
    m = re.search(r"Drafted by (.+?)[,\s]+(\d{4})", h) or re.search(r"(\d{4})[,\s]+Drafted by (.+)", h)
    if m:
        if re.match(r"Drafted by", h):
            full, yr = m.group(1).strip(), int(m.group(2))
        else:
            yr, full = int(m.group(1)), m.group(2).strip()
        abbr = FULL_TO_ABBR.get(full, full)
        return [
            {"type": "draft_year",  "label": f"Draft Class: {yr}", "value": yr},
            {"type": "draft_club",  "label": f"Drafted by {full}", "value": canonical(abbr)},
        ]

    # 複合型: "Drafted 2014, QB" / "Draft 2020, WR"
    m = re.search(r"[Dd]raft(?:ed)?\s+(\d{4})[,\s]+([A-Z]+)$", h)
    if m:
        yr, pos = int(m.group(1)), m.group(2).strip().upper()
        return [
            {"type": "draft_year", "label": f"Draft Class: {yr}", "value": yr},
            {"type": "position",   "label": f"Position: {pos}",   "value": pos},
        ]

    # ----------------------------------------------------------------
    # 単体型
    # ----------------------------------------------------------------
    if re.match(r"Draft Class:\s*\d{4}$", h):
        yr = int(re.search(r"\d{4}", h).group())
        return [{"type": "draft_year", "label": h, "value": yr}]  # レガシー形式

    if re.match(r"Draft Round:\s*\d+$", h):
        rd = int(re.search(r"\d+", h).group())
        return [{"type": "draft_round", "label": h, "value": rd}]  # レガシー形式

    # "1st Round Pick (#6 Overall)" or "Nth overall pick" (any ordinal)
    m = re.search(r"#?(\d+)\s+[Oo]verall", h) or re.search(r"(\d+)(?:st|nd|rd|th)\s+overall\s+pick", h)
    if m:
        pk = int(m.group(1))
        return [{"type": "draft_pick_exact", "label": h, "value": pk}]

    if h.startswith("Drafted by "):
        full = h[len("Drafted by "):]
        abbr = FULL_TO_ABBR.get(full, full)
        return [{"type": "draft_club", "label": h, "value": canonical(abbr)}]

    if h.startswith("College: "):
        return [{"type": "college", "label": h, "value": h.split(": ", 1)[1]}]

    if h.startswith("Position: "):
        return [{"type": "position", "label": h, "value": h.split(": ", 1)[1].upper()}]

    if h.startswith("Award: "):
        return [{"type": "award", "label": h, "value": h[len("Award: "):]}]

    if "Teammate" in h:
        m = re.match(r"^(\d{4}) (.+) Teammate$", h)
        if m:
            yr = int(m.group(1))
            full = m.group(2)
            abbr = FULL_TO_ABBR.get(full, full)
            return [{"type": "teammate", "label": h,
                     "value": {"team": canonical(abbr), "seasons": [yr], "min_overlap": 1}}]
        else:
            full = h.replace(" Teammate", "")
            abbr = FULL_TO_ABBR.get(full, full)
            team_c = canonical(abbr)
            # ヒント選手2人がそのチームにいた全シーズン
            all_seasons = sorted(
                rosters[rosters["team_c"] == team_c]["season"].unique().tolist()
            )
            return [{"type": "teammate", "label": h,
                     "value": {"team": team_c, "seasons": all_seasons, "min_overlap": 2}}]

    if h.startswith("Played for "):
        full = h[len("Played for "):]
        abbr = FULL_TO_ABBR.get(full, full)
        return [{"type": "team_played", "label": h, "value": canonical(abbr)}]

    print(f"  [WARN] Unknown hint format: '{h}'")
    return []


def match_compound(criteria_list: list, pool: list, rosters: pd.DataFrame, awards: dict) -> set:
    """compound criteria（リスト）の全条件 AND でマッチする選手セットを返す"""
    if not criteria_list:
        return set(pool)
    result = players_matching(criteria_list[0], pool, rosters, awards)
    for c in criteria_list[1:]:
        result &= players_matching(c, pool, rosters, awards)
    return result


def main():
    print("Loading nflverse data...")
    awards = load_awards()
    raw_players = load_nflverse_players()
    rosters = load_nflverse_seasonal_rosters(ROSTER_YEARS)
    draft = load_nflverse_draft_picks()

    rosters = rosters.copy()
    rosters["team_c"] = rosters["team"].apply(canonical)
    if "draft_club" in rosters.columns:
        rosters["draft_club_c"] = rosters["draft_club"].apply(
            lambda x: canonical(x) if pd.notna(x) else ""
        )

    if "pfr_id" in rosters.columns:
        draft_cols = draft.rename(columns={
            "pfr_player_id": "pfr_id",
            "round": "draft_round",
            "pick": "draft_pick_number",
        })
        join_cols = ["pfr_id", "draft_round", "draft_pick_number"]
        if "w_av" in draft.columns:
            join_cols.append("w_av")
        draft_join = (
            draft_cols[[c for c in join_cols if c in draft_cols.columns]]
            .drop_duplicates("pfr_id")
        )
        conflict = [c for c in draft_join.columns if c != "pfr_id" and c in rosters.columns]
        if conflict:
            rosters = rosters.drop(columns=conflict)
        rosters = rosters.merge(draft_join, on="pfr_id", how="left")

    agg = rosters.groupby("player_name")["season"].nunique().reset_index(name="n_seasons")
    pool = agg[agg["n_seasons"] >= MIN_SEASONS]["player_name"].tolist()
    print(f"Pool size: {len(pool)}\n")

    puzzles_dir = Path("src/data/puzzles")
    all_ok = True

    for day in TARGET_DAYS:
        path = puzzles_dir / f"day_{day}.json"
        if not path.exists():
            print(f"Day {day}: FILE NOT FOUND\n")
            continue

        data = json.loads(path.read_text())
        target = data["answer"]["name"]

        color_criteria = []
        for color in ("red", "green", "blue"):
            conn = data["connections"][color]
            crits = hint_to_criteria(conn["hint"], conn["players"], rosters)
            color_criteria.append((conn["hint"], crits))

        # 3色それぞれの matching set を求め、交集合を取る
        sets = [match_compound(crits, pool, rosters, awards) for _, crits in color_criteria]
        inter = sets[0] & sets[1] & sets[2]

        if inter == {target}:
            status = "✅ UNIQUE"
        elif target in inter:
            status = f"⚠️  NOT UNIQUE ({len(inter)} match)"
        elif not inter:
            status = "❌ EMPTY INTERSECTION (criteria too strict?)"
        else:
            status = f"❌ TARGET NOT IN INTERSECTION"

        print(f"Day {day} – {target}  {status}")
        for (hint_label, crits), s in zip(color_criteria, sets):
            crit_desc = " AND ".join(c["label"] for c in crits) if crits else hint_label
            print(f"  {crit_desc:60s} → {len(s)}")
        if inter != {target}:
            all_ok = False
            if target in inter:
                others = sorted(inter - {target})[:8]
                print(f"  Also matches: {others}")
            elif inter:
                print(f"  Intersection: {sorted(inter)[:10]}")
        print()

    print("=" * 60)
    print("All unique! ✅" if all_ok else "Issues found – see above ⚠️")


if __name__ == "__main__":
    main()
