"""
generate_puzzles.py
NFLパズル「Asterisk NFL」の問題データを自動生成するスクリプト。

データソース: nflverse GitHub Releases (parquet 直接取得)
  将来の公式 Python ライブラリへの移行は load_nflverse_*() 3関数を差し替えるだけ。

写真: Wikipedia REST API（要 requests ライブラリ）
  ライセンス: CC BY-SA。photo_credit フィールドに出典 URL を格納。

コメント: src/data/playerdescription.md から自動で読み込む。
  書き方は同ファイル冒頭のガイド参照。

Usage:
    python3 generate_puzzles.py
"""

import json
import random
import itertools
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Set

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# 同名別人対策: pfr_id / Wikipedia タイトルの手動 override
# ============================================================

# 同名別人が存在し、display_name の重複排除で意図しない選手が入る場合に明示指定する
PFR_ID_OVERRIDES: Dict[str, str] = {
    "Michael Thomas": "ThomMi05",  # Saints WR (#13) / ThomMi02 は Safety
}

# Wikipedia 記事タイトルが曖昧ページや別人にヒットする場合に正しいタイトルを指定する
WIKI_TITLE_OVERRIDES: Dict[str, str] = {
    "Michael Thomas": "Michael_Thomas_(wide_receiver,_born_1993)",
}

# ============================================================
# Wikipedia REST API による選手写真取得
# ============================================================

def fetch_wikipedia_photo(player_name: str) -> dict:
    """
    Wikipedia REST API から選手の写真サムネイル URL と出典を取得する。
    見つからない場合は空の dict を返す。

    ライセンス: Wikipedia 画像は CC BY-SA が多い。
    出典は photo_credit に Wikipedia ページ URL を格納。

    同名の非NFL選手ページ（disambiguation）にヒットする問題を回避するため、
    フットボール関連のキーワードが description に含まれない場合はフォールバックタイトルを試みる。
    """
    FOOTBALL_KEYWORDS = {
        "nfl", "football", "quarterback", "wide receiver", "running back",
        "tight end", "linebacker", "cornerback", "safety", "defensive",
        "offensive", "super bowl", "nfl draft",
    }
    FALLBACK_SUFFIXES = [
        "_(wide_receiver)",
        "_(American_football)",
        "_(football)",
        "_(NFL)",
    ]

    def _try_title(title: str):
        """指定タイトルで Wikipedia を検索し、(data, thumb, page_url) を返す。失敗時は None。"""
        try:
            import requests
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
            r = requests.get(url, timeout=6, headers={"User-Agent": "AsteriskNFL/1.0"})
            if r.status_code != 200:
                return None
            data = r.json()
            if data.get("type") == "disambiguation":
                return None
            thumb = data.get("thumbnail")
            if not thumb:
                return None
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            return data, thumb, page_url
        except Exception:
            return None

    def _is_football_page(data: dict) -> bool:
        desc = (data.get("description", "") + " " + data.get("extract", "")).lower()
        return any(kw in desc for kw in FOOTBALL_KEYWORDS)

    try:
        # モジュールレベルの override タイトルが指定されていればそれを最優先で使う
        override_title = WIKI_TITLE_OVERRIDES.get(player_name)
        if override_title:
            result = _try_title(override_title)
            if result:
                _, thumb, page_url = result
                return {
                    "photo_url":    thumb["source"],
                    "photo_credit": f"Wikipedia – {page_url}",
                }
            # override があっても取得失敗した場合は通常フローへ

        base_title = player_name.replace(" ", "_")

        # まず素の名前で試みる
        result = _try_title(base_title)

        # フットボール関連ページかチェック；違えばフォールバックを試みる
        if result and not _is_football_page(result[0]):
            print(f"    [INFO] '{base_title}' Wikipedia page doesn't look like NFL player – trying fallbacks")
            result = None

        if result is None:
            for suffix in FALLBACK_SUFFIXES:
                alt = base_title + suffix
                result = _try_title(alt)
                if result and _is_football_page(result[0]):
                    print(f"    [INFO] Found via fallback title: {alt}")
                    break
                result = None

        if result is None:
            return {}

        _, thumb, page_url = result
        return {
            "photo_url":    thumb["source"],
            "photo_credit": f"Wikipedia – {page_url}",
        }
    except Exception as e:
        print(f"    [WARN] Wikipedia photo fetch failed for {player_name}: {e}")
        return {}

# ============================================================
# playerdescription.md からコメントを読み込む
# ============================================================

PLAYER_DESCRIPTION_PATH = Path("src/data/playerdescription.md")

def load_player_descriptions() -> Dict[str, str]:
    """
    src/data/playerdescription.md を解析して { 選手名: コメント } を返す。

    フォーマット:
        選手名（1行）
        コメント本文（1段落）

        次の選手名
        ...
    先頭の # / ## 行と --- はスキップ。
    """
    if not PLAYER_DESCRIPTION_PATH.exists():
        print("  [INFO] playerdescription.md not found – comments will be empty")
        return {}

    result: Dict[str, str] = {}
    blocks = PLAYER_DESCRIPTION_PATH.read_text(encoding="utf-8").split("\n\n")
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines()
                 if l.strip() and not l.startswith("#") and l.strip() != "---"]
        if len(lines) >= 2:
            name    = lines[0]
            comment = " ".join(lines[1:])   # 複数行でも1段落に結合
            result[name] = comment
    print(f"  Descriptions loaded: {len(result)} players")
    return result

# ============================================================
# nflverse データ取得レイヤー（差し替え可能）
# ============================================================

NFLVERSE_BASE = "https://github.com/nflverse/nflverse-data/releases/download"

def load_nflverse_players() -> pd.DataFrame:
    url = f"{NFLVERSE_BASE}/players/players.parquet"
    print(f"    GET {url}")
    return pd.read_parquet(url)

def load_nflverse_seasonal_rosters(years: List[int]) -> pd.DataFrame:
    frames = []
    for yr in years:
        url = f"{NFLVERSE_BASE}/rosters/roster_{yr}.parquet"
        try:
            frames.append(pd.read_parquet(url))
        except Exception as e:
            print(f"    [WARN] roster {yr}: {e}")
    if not frames:
        raise RuntimeError("No roster data loaded.")
    df = pd.concat(frames, ignore_index=True)
    df.dropna(subset=["gsis_id"], inplace=True)
    if "full_name" in df.columns and "player_name" not in df.columns:
        df = df.rename(columns={"full_name": "player_name"})
    return df

def load_nflverse_draft_picks() -> pd.DataFrame:
    url = f"{NFLVERSE_BASE}/draft_picks/draft_picks.parquet"
    print(f"    GET {url}")
    return pd.read_parquet(url)

# ============================================================
# 設定パラメータ
# ============================================================

ROSTER_YEARS   = list(range(2010, 2026))  # 2025シーズンも取得
MIN_SEASONS    = 3          # 一意性テスト用プールの最低シーズン数
HINT_TOP_POOL  = 10         # ヒント候補の上位プールサイズ（この中からランダム選択）
MAX_COMBO_TRY  = 3000
TEAM_CRIT_TYPES = {"team_played", "teammate"}
MAX_TEAM_CRIT   = 1

# ---- ヒント選手の知名度スコア ----
# w_av（加重キャリアAV）をベースに、2015年以降も活躍している選手を優遇する
# fame_score = w_av * recency_bonus
# recency_bonus = 1.0 + 0.1 * max(0, last_season - 2015)
RECENCY_BASE_YEAR = 2015
RECENCY_WEIGHT    = 0.1     # 1年あたり +10%

# ---- position criterion から除外するポジション ----
# 選手目線で「情報量が少ない（QB等）」か「区分が曖昧（DL/OLB等）」なものを除外
POSITION_EXCLUDED = {
    # オフェンス: 多すぎて絞り込みにならない
    "QB", "WR", "RB",
    # OL: ラベルが多様で混乱しやすい
    "OT", "OG", "T", "G", "OL",
    # DB: 多すぎる
    "CB", "S", "SS", "FS", "DB",
    # DL/LB: 呼び方が時代・チームで変わる
    "DE", "DT", "NT", "DL",
    "LB", "OLB", "ILB", "MLB", "EDGE",
    # 同名別人との混同リスク（TE / C は有名な同姓同名選手が他ポジションにいがち）
    "TE", "C",
}
# POSITION_EXCLUDED に含まれないもの（K, P, LS, FB 等）は有効な Criteria として使う

# ---- 単年チームメイト criterion を許可する SB 優勝ロスター ----
# (シーズン年, チーム略称) のセット。例: 2021年シーズン = SB LVI 優勝 LAR
SUPERBOWL_CHAMPS: Set[Tuple[int, str]] = {
    (2010, "GB"),  (2011, "NYG"), (2012, "BAL"), (2013, "SEA"),
    (2014, "NE"),  (2015, "DEN"), (2016, "NE"),  (2017, "PHI"),
    (2018, "NE"),  (2019, "KC"),  (2020, "TB"),  (2021, "LA"),
    (2022, "KC"),  (2023, "KC"),  (2024, "PHI"), (2025, "SEA"),
}

# チーム移転マッピング（旧略称 → 現略称）
# nflverse では年度によって WAS / WSH の両方が使われるため WSH → WAS に統一
TEAM_MOVES = {
    "SD":  "LAC",   # San Diego Chargers
    "STL": "LA",    # St. Louis Rams
    "OAK": "LV",    # Oakland Raiders
    "WSH": "WAS",   # Washington（Redskins/Football Team/Commanders）
}

def canonical(t: str) -> str:
    t = str(t).strip()
    return TEAM_MOVES.get(t, t)

# チーム略称 → フルネーム（teammate / team_played のラベル表示用）
TEAM_FULL_NAMES: Dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB":  "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC":  "Kansas City Chiefs",
    "LA":  "Los Angeles Rams",
    "LAC": "Los Angeles Chargers",
    "LV":  "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE":  "New England Patriots",
    "NO":  "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF":  "San Francisco 49ers",
    "TB":  "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
    # 移転前の旧略称も念のため
    "BLT": "Baltimore Ravens",
    "OAK": "Las Vegas Raiders",
    "SD":  "Los Angeles Chargers",
    "STL": "Los Angeles Rams",
    "WSH": "Washington Commanders",
}

def team_full(abbr: str) -> str:
    """チーム略称をフルネームに変換。未知の略称はそのまま返す。"""
    return TEAM_FULL_NAMES.get(canonical(abbr), abbr)

# ============================================================
# アワードデータ読み込み
# ============================================================

AWARDS_DIR = Path("awardsdata")

def load_awards() -> Dict[str, List[str]]:
    award_files = {
        "MVP.csv":     "MVP",
        "OPoY.csv":    "Offensive Player of the Year",
        "DPoY.csv":    "Defensive Player of the Year",
        "ORoY.csv":    "Offensive Rookie of the Year",
        "DRoY.csv":    "Defensive Rookie of the Year",
        "CPoY.csv":    "Comeback Player of the Year",
        "heisman.csv": "Heisman Trophy",
        "SBMVP.csv":   "Super Bowl MVP",
        "WPMoY.csv":   "Walter Payton Man of the Year",
    }
    award_map: Dict[str, List[str]] = {}
    for filename, award_name in award_files.items():
        path = AWARDS_DIR / filename
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
            name_col = next((c for c in df.columns if c.lower() in ("player", "name")), None)
            if not name_col:
                continue
            for raw in df[name_col].dropna():
                name = str(raw).replace("*", "").strip()
                award_map.setdefault(name, []).append(award_name)
        except Exception as e:
            print(f"  [WARN] {filename}: {e}")
    print(f"  Awards: {len(award_map)} players")
    return award_map

# ============================================================
# nflverse データ読み込み・加工
# ============================================================

def load_all_data() -> Tuple[pd.DataFrame, pd.DataFrame, List[str], Dict[str, float], Dict[str, int], Dict[str, dict]]:
    """
    Returns:
        rosters      : ロースター行（正規化・draft_round 付き）
        players_db   : 全選手マスター（playerDatabase 生成用）
        pool         : 一意性テスト用選手名リスト
        fame_scores  : player_name → 知名度スコア（w_av × recency_bonus）
        draft_picks_n: player_name → ドラフト指名順位（Draft Class hint のソート用）
        player_ids   : player_name → {"pfr_id": ..., "espn_id": ..., "pfr_url": ..., "espn_url": ...}
    """
    print("  Fetching player master...")
    raw_players = load_nflverse_players()

    print(f"  Fetching seasonal rosters {ROSTER_YEARS[0]}–{ROSTER_YEARS[-1]}...")
    rosters = load_nflverse_seasonal_rosters(ROSTER_YEARS)

    print("  Fetching draft picks...")
    draft = load_nflverse_draft_picks()

    # ---- roster 加工 ----
    rosters = rosters.copy()
    rosters["team_c"] = rosters["team"].apply(canonical)
    if "draft_club" in rosters.columns:
        rosters["draft_club_c"] = rosters["draft_club"].apply(
            lambda x: canonical(x) if pd.notna(x) else ""
        )

    # draft_round, w_av, pick を pfr_id で結合
    # ※ roster parquet 自体にも draft 系列が含まれる場合があるため、
    #   merge 前に衝突列を削除して draft_picks の値を優先させる
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
        # merge 前に衝突列を削除（_x / _y 汚染防止）
        conflict = [c for c in draft_join.columns if c != "pfr_id" and c in rosters.columns]
        if conflict:
            rosters = rosters.drop(columns=conflict)
        rosters = rosters.merge(draft_join, on="pfr_id", how="left")
    else:
        rosters["draft_round"] = None
        rosters["draft_pick_number"] = None
        rosters["w_av"] = None

    # ---- 知名度スコアを計算 ----
    # w_av: 加重キャリアAV（PFR）。最近のシーズンがより重く計上されている
    # last_season: rosters での最終出場シーズン
    player_last_season = (
        rosters.groupby("player_name")["season"].max().to_dict()
    )
    # w_av は全行で同値なので first() で取得
    if "w_av" in rosters.columns:
        player_wav = (
            rosters.groupby("player_name")["w_av"]
            .first()
            .fillna(0)
            .to_dict()
        )
    else:
        player_wav = {}

    def calc_fame(name: str) -> float:
        wav = player_wav.get(name, 0) or 0
        last = player_last_season.get(name, 2010)
        recency = 1.0 + RECENCY_WEIGHT * max(0, last - RECENCY_BASE_YEAR)
        # w_av が 0（未指名等）の場合、出場シーズン数 × 5 を代替値として使う
        if wav == 0:
            n_seasons = rosters[rosters["player_name"] == name]["season"].nunique()
            wav = n_seasons * 5
        return wav * recency

    fame_scores = {name: calc_fame(name) for name in rosters["player_name"].dropna().unique()}

    # ドラフト指名順位（draft_year criterion のソート用: 小さいほど上位指名）
    if "draft_pick_number" in rosters.columns:
        draft_picks_n = (
            rosters.groupby("player_name")["draft_pick_number"]
            .first()
            .dropna()
            .astype(int)
            .to_dict()
        )
    else:
        draft_picks_n = {}

    # ---- playerDatabase（全選手） ----
    roster_gsis = set(rosters["gsis_id"].dropna().tolist())
    id_cols = ["display_name", "gsis_id"]
    if "position" in raw_players.columns:
        id_cols.append("position")
    if "pfr_id" in raw_players.columns:
        id_cols.append("pfr_id")
    if "espn_id" in raw_players.columns:
        id_cols.append("espn_id")

    # player_ids 用: display_name 単位で重複排除（PFR/ESPN リンク辞書に使用）
    players_db = (
        raw_players[raw_players["gsis_id"].isin(roster_gsis)]
        [id_cols]
        .dropna(subset=["display_name"])
        .drop_duplicates("display_name")
    )
    print(f"  Full player DB: {len(players_db)} players")

    # 検索ドロップダウン用: 同名異ポジション選手を両方残す（例: Alex Smith QB / TE）
    search_dedup_cols = ["display_name", "position"] if "position" in id_cols else ["display_name"]
    players_search = (
        raw_players[raw_players["gsis_id"].isin(roster_gsis)]
        [id_cols]
        .dropna(subset=["display_name"])
        .drop_duplicates(search_dedup_cols)
    )
    print(f"  Search player DB (with pos): {len(players_search)} entries")

    # ---- player_ids（PFR / ESPN リンク用） ----
    # pfr_id 例: "BradTo00" → URL: https://www.pro-football-reference.com/players/B/BradTo00.htm
    # espn_id 例: 2330 → URL: https://www.espn.com/nfl/player/_/id/2330
    player_ids: Dict[str, dict] = {}
    for _, row in players_db.iterrows():
        name = row["display_name"]
        pfr_id  = row.get("pfr_id",  None) if "pfr_id"  in row.index else None
        espn_id = row.get("espn_id", None) if "espn_id" in row.index else None
        entry: dict = {}
        if pd.notna(pfr_id) and str(pfr_id).strip():
            pid = str(pfr_id).strip()
            entry["pfr_id"]  = pid
            entry["pfr_url"] = f"https://www.pro-football-reference.com/players/{pid[0].upper()}/{pid}.htm"
        if pd.notna(espn_id):
            eid = str(int(float(espn_id)))
            entry["espn_id"]  = eid
            entry["espn_url"] = f"https://www.espn.com/nfl/player/_/id/{eid}"
        if entry:
            player_ids[name] = entry

    # ---- 一意性テスト用プール ----
    agg = rosters.groupby("player_name")["season"].nunique().reset_index(name="n_seasons")
    pool = agg[agg["n_seasons"] >= MIN_SEASONS]["player_name"].tolist()
    print(f"  Uniqueness pool: {len(pool)} players")

    return rosters, players_db, players_search, pool, fame_scores, draft_picks_n, player_ids

# ============================================================
# Criteria 生成
# ============================================================

def build_criteria(
    target: str,
    rosters: pd.DataFrame,
    awards: Dict[str, List[str]],
    player_ids: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    # pfr_id が利用可能な場合は pfr_id でフィルタ（同名別人の混入を防ぐ）
    target_pfr = (player_ids or {}).get(target, {}).get("pfr_id") if player_ids else None
    if target_pfr and "pfr_id" in rosters.columns:
        rows = rosters[rosters["pfr_id"] == target_pfr]
        if rows.empty:
            # pfr_id で見つからなければ名前にフォールバック
            rows = rosters[rosters["player_name"] == target]
    else:
        rows = rosters[rosters["player_name"] == target]

    if rows.empty:
        print(f"  [WARN] '{target}' not in rosters")
        return []

    latest = rows.sort_values("season", ascending=False).iloc[0]
    criteria: List[dict] = []

    # ---- College ----
    # "Delaware; Pittsburgh" のような転校生表記は最初の大学（在籍期間が長い方）を使う
    college_raw = str(latest.get("college", "")).strip()
    college = college_raw.split(";")[0].strip() if ";" in college_raw else college_raw
    if college and college.lower() not in ("nan", "", "none"):
        criteria.append({"type": "college", "label": f"College: {college}", "value": college})

    # ---- Position（除外リスト以外のみ） ----
    pos = str(latest.get("position", "")).strip().upper()
    if pos and pos not in ("NAN", "", "NONE") and pos not in POSITION_EXCLUDED:
        criteria.append({"type": "position", "label": f"Position: {pos}", "value": pos})

    # ---- Draft Year ----
    entry_year = latest.get("entry_year")
    # ---- Draft criteria ----
    # 1巡 + 全体順位あり → draft_pick_exact（最も具体的・ヒント選手も同順位の選手）
    # 1巡 + 順位なし / 2〜7巡 → draft_year_round 複合型（"Draft Class: YYYY Round N"）
    # UDFA（draft_round なし）→ udfa 型（年不問でひとまとめ）
    dr = latest.get("draft_round")
    if pd.notna(dr):
        rd = int(dr)
        if rd == 1:
            pk = latest.get("draft_pick_number")
            if pd.notna(pk):
                pk_int = int(pk)
                criteria.append({
                    "type": "draft_pick_exact",
                    "label": f"1st Round Pick (#{pk_int} Overall)",
                    "value": pk_int,
                })
            elif pd.notna(entry_year):
                yr = int(entry_year)
                criteria.append({
                    "type": "draft_year_round",
                    "label": f"Draft Class: {yr} Round 1",
                    "value": {"year": yr, "round": 1},
                })
        elif 2 <= rd <= 7 and pd.notna(entry_year):
            yr = int(entry_year)
            criteria.append({
                "type": "draft_year_round",
                "label": f"Draft Class: {yr} Round {rd}",
                "value": {"year": yr, "round": rd},
            })
    elif pd.notna(entry_year):
        # ドラフト指名なし = UDFA（年不問でひとまとめ）
        criteria.append({
            "type": "udfa",
            "label": "Undrafted Free Agent (UDFA)",
            "value": None,
        })

    # ---- Draft Club ----
    dc = str(latest.get("draft_club_c", "")).strip()
    if dc and dc.lower() not in ("nan", "", "none"):
        criteria.append({"type": "draft_club", "label": f"Drafted by {team_full(dc)}", "value": dc})

    # ---- Teams Played For ----
    seen_teams: Set[str] = set()
    team_seasons_map: Dict[str, List[int]] = {}
    for _, ts in rows[["season", "team_c"]].drop_duplicates().iterrows():
        team = ts["team_c"]
        season = int(ts["season"])
        team_seasons_map.setdefault(team, []).append(season)

    for team, seasons in team_seasons_map.items():
        seasons_sorted = sorted(seasons)
        seen_teams.add(team)

        # Played for（チーム所属経験）
        criteria.append({"type": "team_played", "label": f"Played for {team_full(team)}", "value": team})

        # Teammate criterion
        n = len(seasons_sorted)
        if n >= 2:
            # 複数年在籍 → 「チームのチームメイト」表記（年は内部データのみ、ラベルには出さない）
            # 例: "New Orleans Saints Teammate"
            # ※ 年範囲をラベルに入れると「全員がその期間ずっとそのチームにいた」と誤解される
            full_name = team_full(team)
            criteria.append({
                "type": "teammate",
                "label": f"{full_name} Teammate",
                "value": {"team": team, "seasons": seasons_sorted, "min_overlap": 2},
            })
        else:
            # 単年在籍 → SB 優勝チームのみ許可
            # 例: "2021 Los Angeles Rams Teammate"（特定シーズンのロスターが意味を持つ）
            s = seasons_sorted[0]
            if (s, team) in SUPERBOWL_CHAMPS:
                full_name = team_full(team)
                criteria.append({
                    "type": "teammate",
                    "label": f"{s} {full_name} Teammate",
                    "value": {"team": team, "seasons": [s], "min_overlap": 1},
                })

    # ---- Awards ----
    for award in set(awards.get(target, [])):
        criteria.append({"type": "award", "label": f"Award: {award}", "value": award})

    return criteria

# ============================================================
# Criterion → マッチする選手セット
# ============================================================

def players_matching(
    criterion: dict,
    pool: List[str],
    rosters: pd.DataFrame,
    awards: Dict[str, List[str]],
) -> Set[str]:
    ctype, val = criterion["type"], criterion["value"]
    pool_set = set(pool)
    pr = rosters[rosters["player_name"].isin(pool_set)]

    if ctype == "college":
        matched = pr[pr["college"] == val]["player_name"].unique()

    elif ctype == "position":
        matched = pr[pr["position"].str.upper() == val]["player_name"].unique()

    elif ctype == "draft_year_round":
        # 複合型: 年 + ラウンドの AND 条件
        yr, rd = val["year"], val["round"]
        if "draft_round" in pr.columns:
            matched = pr[
                (pr["entry_year"] == yr) & (pr["draft_round"] == rd)
            ]["player_name"].unique()
        else:
            matched = pr[pr["entry_year"] == yr]["player_name"].unique()

    elif ctype == "udfa":
        # 年不問でアンドラフト選手全員
        if "draft_round" in pr.columns:
            matched = pr[pr["draft_round"].isna()]["player_name"].unique()
        else:
            matched = []

    elif ctype == "draft_pick_exact":
        # 1巡の同じ全体指名順位の選手（例: #6 Overall → 歴代の全体6位指名選手）
        # draft_round == 1 も同時に確認して 2巡以降の同 pick 番号との混同を防ぐ
        if "draft_pick_number" in pr.columns and "draft_round" in pr.columns:
            matched = pr[
                (pr["draft_round"] == 1) & (pr["draft_pick_number"] == val)
            ]["player_name"].unique()
        elif "draft_pick_number" in pr.columns:
            matched = pr[pr["draft_pick_number"] == val]["player_name"].unique()
        else:
            matched = []

    elif ctype == "draft_club":
        matched = pr[pr["draft_club_c"] == val]["player_name"].unique() if "draft_club_c" in pr.columns else []

    elif ctype == "team_played":
        matched = pr[pr["team_c"] == val]["player_name"].unique()

    elif ctype == "teammate":
        team     = val["team"]
        seasons  = val["seasons"]
        min_ovlp = val.get("min_overlap", 1)
        # 対象チーム × 対象シーズン群でのロースター登場回数
        overlap = (
            pr[(pr["team_c"] == team) & (pr["season"].isin(seasons))]
            .groupby("player_name")["season"].nunique()
        )
        matched = overlap[overlap >= min_ovlp].index.tolist()

    elif ctype == "award":
        matched = [n for n in pool if val in awards.get(n, [])]

    else:
        matched = []

    return set(matched) & pool_set

# ============================================================
# 一意性チェック
# ============================================================

def check_unique(
    triple: tuple,
    target: str,
    pool: List[str],
    rosters: pd.DataFrame,
    awards: Dict[str, List[str]],
) -> Tuple[bool, Set[str]]:
    s = [players_matching(c, pool, rosters, awards) for c in triple]
    inter = s[0] & s[1] & s[2]
    return (inter == {target}), inter

def _criterion_team(c: dict) -> Optional[str]:
    ctype = c["type"]
    if ctype == "team_played":
        return canonical(c["value"])
    elif ctype == "teammate":
        return canonical(c["value"]["team"])
    elif ctype == "draft_club":
        return canonical(c["value"])
    return None

def is_valid_combo(combo: tuple) -> bool:
    """
    有効な triple かチェック:
      1. team_played / teammate は最大 MAX_TEAM_CRIT 個まで
      2. 複数 criterion が同一チームを参照していたらNG
         例: Teammates on NYJ(...) + Drafted by NYJ → 同チームNG
             Teammates on NYJ(...) + Drafted by SEA → 別チームOK
    """
    n_team = sum(1 for c in combo if c["type"] in TEAM_CRIT_TYPES)
    if n_team > MAX_TEAM_CRIT:
        return False
    teams = [t for c in combo if (t := _criterion_team(c)) is not None]
    if len(teams) != len(set(teams)):
        return False
    return True

# ============================================================
# ヒント選手選定
# ============================================================

def pick_hints(
    criterion: dict,
    target: str,
    pool: List[str],
    rosters: pd.DataFrame,
    awards: Dict[str, List[str]],
    fame_scores: Dict[str, float],
    draft_picks_n: Dict[str, int],
    n: int = 2,
    excluded: Optional[Set[str]] = None,
) -> List[str]:
    """
    criterion にマッチする選手からヒント選手を n 人選ぶ。

    criterion 別ソート基準:
      - draft_year     : ドラフト指名順位（pick番号）昇順 = 同年上位指名を優先
      - draft_pick_exact: 知名度スコア降順（同じ全体順位 = 少人数なので fame 順が自然）
      - その他（college含む）: 知名度スコア（w_av × recency_bonus）降順

    選定プロセス:
      1. マッチする全候補を取得
      2. 基準でソートし上位 HINT_TOP_POOL 人を候補プールとして確定
      3. その中からランダムに n 人選ぶ（毎回少し変化させるため）
    """
    _excluded = (excluded or set()) | {target}
    matched = players_matching(criterion, pool, rosters, awards) - _excluded

    ctype = criterion["type"]

    if False:
        pass  # 将来の分岐用プレースホルダー

    else:
        # college / draft_round / draft_pick_exact / team_played / teammate / award など
        # すべて知名度スコア（w_av × recency_bonus）降順
        ranked = sorted(
            matched,
            key=lambda p: fame_scores.get(p, 0),
            reverse=True,
        )

    top = ranked[:HINT_TOP_POOL]
    if len(top) < n:
        top = ranked  # 候補が少なければ全員を対象に

    return random.sample(top, min(n, len(top)))

# ============================================================
# パズル生成
# ============================================================

def generate_puzzle(
    target: str,
    day_id: int,
    date_str: str,
    pool: List[str],
    rosters: pd.DataFrame,
    players_db: pd.DataFrame,
    awards: Dict[str, List[str]],
    fame_scores: Dict[str, float],
    draft_picks_n: Dict[str, int],
    player_ids: Dict[str, dict],
    descriptions: Dict[str, str],
) -> Optional[dict]:

    print(f"\n{'─'*55}")
    print(f"  Day {day_id}  {date_str}  |  {target}")

    criteria = build_criteria(target, rosters, awards, player_ids)
    print(f"  Criteria candidates: {len(criteria)}")
    if len(criteria) < 3:
        print("  [ERROR] Not enough criteria. Skip.")
        return None

    # ---- ヒント候補数を事前計算（各 criterion で target 除外後の人数）----
    hint_avail: Dict[str, int] = {
        c["label"]: len(players_matching(c, pool, rosters, awards) - {target})
        for c in criteria
    }

    def has_good_hints(combo: tuple) -> bool:
        """combo 内の全 criterion がヒント選手 2 人以上持つか"""
        return all(hint_avail[c["label"]] >= 2 for c in combo)

    # ---- 一意 triple を探す ----
    # 優先順: (1) UNIQUE + good hints  (2) UNIQUE  (3) best match count + good hints  (4) best
    best_triple:       Optional[tuple] = None
    best_size:         Optional[int]   = None
    best_inter:        Optional[Set]   = None
    best_good_triple:  Optional[tuple] = None  # good hints があるベスト
    best_good_size:    Optional[int]   = None
    best_good_inter:   Optional[Set]   = None
    found      = False
    found_good = False  # UNIQUE かつ good hints

    teammate_crit = [c for c in criteria if c["type"] == "teammate"]
    other_crit    = [c for c in criteria if c["type"] not in TEAM_CRIT_TYPES]

    # フェーズ A: teammate 1 + 非チーム系 2 の組み合わせを優先
    mixed: List[tuple] = []
    if teammate_crit and len(other_crit) >= 2:
        for tm in teammate_crit:
            for pair in itertools.combinations(other_crit, 2):
                mixed.append((tm, *pair))
        random.shuffle(mixed)

    for combo in mixed[:MAX_COMBO_TRY]:
        if not is_valid_combo(combo):
            continue
        is_u, inter = check_unique(combo, target, pool, rosters, awards)
        good = has_good_hints(combo)
        if is_u and good:
            best_triple, best_inter, found = combo, inter, True
            found_good = True
            break
        if is_u and not found:
            best_triple, best_inter, found = combo, inter, True
        if good and (best_good_size is None or len(inter) < best_good_size):
            best_good_size, best_good_triple, best_good_inter = len(inter), combo, inter
        if best_size is None or len(inter) < best_size:
            best_size, best_triple, best_inter = len(inter), combo, inter

    # フェーズ B: 全組み合わせから（フィルター付き）
    if not found_good:
        all_combos = [c for c in itertools.combinations(criteria, 3) if is_valid_combo(c)]
        random.shuffle(all_combos)
        for combo in all_combos[:MAX_COMBO_TRY]:
            if not is_valid_combo(combo):
                continue
            is_u, inter = check_unique(combo, target, pool, rosters, awards)
            good = has_good_hints(combo)
            if is_u and good:
                best_triple, best_inter, found = combo, inter, True
                found_good = True
                break
            if is_u and not found:
                best_triple, best_inter, found = combo, inter, True
            if good and (best_good_size is None or len(inter) < best_good_size):
                best_good_size, best_good_triple, best_good_inter = len(inter), combo, inter
            if best_size is None or len(inter) < best_size:
                best_size, best_triple, best_inter = len(inter), combo, inter

    if best_triple is None:
        print("  [ERROR] No triple found. Skip.")
        return None

    # UNIQUE + good hints が見つからなかった場合、good hints だけでもあれば優先
    if not found_good and best_good_triple is not None:
        best_triple, best_inter = best_good_triple, best_good_inter
        print(f"  [WARN] No unique combo with full hint players — using best combo with good hints")
    elif not found_good:
        # どのcomboもヒント選手不足 → 警告
        short = [c["label"] for c in best_triple if hint_avail[c["label"]] < 2]
        print(f"  [WARN] Hint players < 2 for: {short}")

    tag = "[UNIQUE]" if found else f"[BEST ~{best_size}]"
    print(f"  {tag} {[c['label'] for c in best_triple]}")

    # ---- ヒント開示順を難易度で並べ替え ----
    # 「合致する選手数が多い = 曖昧 = より難しいヒント」を最初に公開し、
    # 「合致する選手数が少ない = 絞り込まれている = より簡単なヒント」を最後に公開する
    # これにより Red(1ミスで開示) が一番曖昧、Blue(3ミスで開示) が一番具体的になる
    def match_count_for(c: dict) -> int:
        return len(players_matching(c, pool, rosters, awards))

    sorted_triple = sorted(best_triple, key=match_count_for, reverse=True)  # 降順
    match_counts = [match_count_for(c) for c in sorted_triple]
    print(f"  Hint order (match counts): {[c['label'] for c in sorted_triple]} {match_counts}")

    # ---- ヒント選手 ----
    connections: Dict[str, dict] = {}
    hint_names: List[str] = []
    color_keys = ["red", "green", "blue"]
    color_codes = {"red": "#ff6b6b", "green": "#2ecc71", "blue": "#3498db"}

    for i, crit in enumerate(sorted_triple):
        color = color_keys[i]
        hints = pick_hints(
            crit, target, pool, rosters, awards, fame_scores, draft_picks_n,
            n=2, excluded=set(hint_names),  # 既出のヒント選手を除外
        )

        # ヒント選手が2人未満の場合は空のままにする（無関係な有名選手で埋めない）

        connections[color] = {
            "colorCode": color_codes[color],
            "hint": crit["label"],
            "players": hints[:2],
        }
        hint_names.extend(hints[:2])

    # ---- PFR / ESPN リンク ----
    answer_links = player_ids.get(target, {})

    # ---- Wikipedia 写真 ----
    print(f"  Fetching Wikipedia photo...")
    photo = fetch_wikipedia_photo(target)
    if photo:
        print(f"  Photo: {photo['photo_url'][:60]}...")
    else:
        print(f"  Photo: not found")

    comment = descriptions.get(target, "")
    if comment:
        print(f"  Comment: {comment[:50]}...")
    else:
        print(f"  Comment: (not found in playerdescription.md)")

    return {
        "id": f"day_{day_id}",
        "date": date_str,
        "answer": {
            "name":    target,
            "comment": comment,
            **photo,              # photo_url, photo_credit（取得できた場合のみ）
            **answer_links,       # pfr_id, pfr_url, espn_id, espn_url
        },
        "connections": connections,
    }

# ============================================================
# エントリーポイント
# ============================================================

def main():
    import datetime
    random.seed(42)

    # ============================================================
    # ターゲット選手リスト（2ヶ月分 = 60人）
    # 開始日 START_DATE から1日ずつ自動で日付を割り当てる
    # 追加するときはリストに選手名を足すだけでOK
    # ============================================================
    START_DATE = datetime.date(2026, 4, 5)

    # Day 1〜10 はすでに確定済み JSON がある → SKIP_IF_EXISTS=True でスキップ
    SKIP_IF_EXISTS = True

    TARGET_PLAYERS = [
        # ---- Day 1〜10: 既存 JSON に合わせた正確な順序 ----
        "Drew Brees",           # Day 1
        "George Kittle",        # Day 2
        "Stephon Gilmore",      # Day 3
        "Ja'Marr Chase",        # Day 4
        "Brandon Aubrey",       # Day 5
        "James Conner",         # Day 6
        "Michael Thomas",       # Day 7
        "Fred Warner",          # Day 8
        "Kirk Cousins",         # Day 9
        "Antonio Brown",        # Day 10
        # ---- Day 11〜31: playerdescription.md 記載順 ----
        "Maxx Crosby",          # Day 11
        "Chris Olave",          # Day 12
        "Austin Ekeler",        # Day 13
        "Jason Kelce",          # Day 14
        "Ryan Fitzpatrick",     # Day 15
        "Nik Bonitto",          # Day 16
        "Kyle Hamilton",        # Day 17
        "Trey Hendrickson",     # Day 18
        "Trent McDuffie",       # Day 19
        "Davante Adams",        # Day 20
        "Alvin Kamara",         # Day 21
        "Cameron Heyward",      # Day 22
        "Zack Baun",            # Day 23
        "Dak Prescott",         # Day 24
        "Cameron Dicker",       # Day 25
        "Trey McBride",         # Day 26
        "DJ Moore",             # Day 27
        "Tristan Wirfs",        # Day 28
        "Jeffery Simmons",      # Day 29
        "Bobby Wagner",         # Day 30
        "Chris Godwin",         # Day 31
    ]

    # 開始日から1日ずつ日付を割り当て
    targets = [
        (name, str(START_DATE + datetime.timedelta(days=i)))
        for i, name in enumerate(TARGET_PLAYERS)
    ]
    end_date = START_DATE + datetime.timedelta(days=len(targets) - 1)

    print("=" * 55)
    print(f"Generating {len(targets)} puzzles: {START_DATE} – {end_date}")
    print("Loading player descriptions...")
    descriptions = load_player_descriptions()
    print("Loading nflverse data...")
    awards = load_awards()
    rosters, players_db, players_search, pool, fame_scores, draft_picks_n, player_ids = load_all_data()

    out_dir = Path("src/data/puzzles")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- playerDatabase を1つの共有 JSON として書き出し ----
    # 形式: [{name: "Aaron Donald", pos: "DT"}, ...] （同名異ポジション選手を両方含む）
    db_entries: list = []
    has_pos = "position" in players_search.columns
    for _, row in players_search.sort_values("display_name").iterrows():
        entry: dict = {"name": row["display_name"]}
        if has_pos:
            pos_val = row.get("position", "")
            if pd.notna(pos_val) and str(pos_val).strip().lower() not in ("", "nan", "none"):
                entry["pos"] = str(pos_val).strip()
        db_entries.append(entry)
    db_path = out_dir / "player_database.json"
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db_entries, f, ensure_ascii=False)
    print(f"  → Saved: {db_path}  ({len(db_entries)} entries)")

    # PFR_ID_OVERRIDES を player_ids に反映する
    # override がある選手は rosters から正しい pfr_id を引いて entry ごと上書き
    for name, pfr_id in PFR_ID_OVERRIDES.items():
        letter = pfr_id[0].upper()
        pfr_url = f"https://www.pro-football-reference.com/players/{letter}/{pfr_id}.htm"
        # espn_id は players_db から引けなければ既存 entry のものを流用
        existing = player_ids.get(name, {})
        player_ids[name] = {
            **existing,
            "pfr_id":  pfr_id,
            "pfr_url": pfr_url,
        }
        print(f"  [OVERRIDE] {name} → pfr_id={pfr_id}")

    results: List[dict] = []
    for day_id, (target, date_str) in enumerate(targets, start=1):
        path = out_dir / f"day_{day_id}.json"
        if SKIP_IF_EXISTS and path.exists():
            existing = json.loads(path.read_text())
            print(f"  → Skipped (exists): {path}  [{existing['answer']['name']}]")
            results.append(existing)
            continue
        puzzle = generate_puzzle(
            target, day_id, date_str,
            pool, rosters, players_db, awards, fame_scores, draft_picks_n, player_ids,
            descriptions,
        )
        if puzzle is None:
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(puzzle, f, ensure_ascii=False, indent=2)
        print(f"  → Saved: {path}")
        results.append(puzzle)

    # 全パズルをまとめた JSON も出力
    all_path = out_dir / f"all_{START_DATE}.json"
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"Done! {len(results)}/{len(targets)} puzzles generated.")
    print()
    for p in results:
        links = " | ".join(filter(None, [p["answer"].get("pfr_url",""), p["answer"].get("espn_url","")]))
        print(f"  [{p['date']}] {p['answer']['name']}  {links[:60]}")
        for color, conn in p["connections"].items():
            print(f"    {color:5s}: {conn['hint']:45s} → {conn['players']}")


if __name__ == "__main__":
    main()
