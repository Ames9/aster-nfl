# プロジェクト概要
NFLの選手名を当てるパズルゲーム「Asterisk NFL」用のデータ生成スクリプト（Python）を作成してください。（アプリ自体はplan.mdとimplementation.mdベースで実装済みでこのフォルダ内に）。
Nflverse(nflverse) または別データを使用し、指定した「正解選手」から逆算して、完全に一意となる3つの共通点（Criteria）と、ヒントとなる周辺選手を自動抽出するロジックを実装します。
参考までに、以前別のプロジェクトでnflverseからのデータ取得に使ったfetchdata_example.py も入れておいたので必要なら参考にして。

---

# 実装済みアルゴリズム（generate_puzzles.py）

## データソース

nflverse の GitHub Releases から直接 parquet を取得する（外部ライブラリ不要）。

```
https://github.com/nflverse/nflverse-data/releases/download/players/players.parquet
https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{year}.parquet
https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.parquet
```

**なぜ `nfl_data_py` / `nflreadpy` を使わないか**
- `nfl_data_py` は上記 URL への薄いラッパーに過ぎず、`pd.read_parquet(url)` と等価
- `nflreadr` は R 専用、`nflreadpy` は Python pip パッケージとして現時点では未公開
- 直接 URL アクセスにすることで外部ライブラリ依存を排除
- データ取得は `load_nflverse_*()` 3関数にカプセル化しており、将来の差し替えはその中だけで済む

## 設定パラメータ（変数化済み）

| 変数 | デフォルト | 意味 |
|------|-----------|------|
| `ROSTER_YEARS` | 2010〜2025 | ロースター取得年範囲（2025シーズン含む）|
| `MIN_SEASONS` | 3 | 一意性テスト用プールへの最低出場シーズン数 |
| `MAX_COMBO_TRY` | 3000 | 一意性チェックの最大試行回数 |
| `MAX_TEAM_CRIT` | 1 | triple 中に許可するチーム系 criterion の最大数 |
| `HINT_TOP_POOL` | 10 | ヒント候補の上位プールサイズ（この中からランダム選択）|
| `RECENCY_BASE_YEAR` | 2015 | 知名度スコアの recency_bonus 基準年 |
| `RECENCY_WEIGHT` | 0.1 | recency_bonus の年あたり重み（1年＋10%）|

## Step 1: プレイヤープールの構築（2種類）

### 一意性テスト用プール（`pool`）
- 2010〜2025 のロースターデータを読み込み
- **`MIN_SEASONS` シーズン以上登場した選手のみ**に絞り込む（約6,300人）
- 無名選手・プラクティスチーム常連などを除外し、問題の質を担保

### playerDatabase（回答入力用）
- `players.parquet`（全選手マスター）と照合し、ロースターに `gsis_id` が存在する選手を全員収録（約10,000人）
- プレイヤーはこのリストから**全選手を選択可能**（正解選手が必ず含まれることを保証）

## Step 2: 知名度スコア（`fame_score`）の計算

ヒント選手の選定に使う「有名さの指標」として、以下を計算する。

### 元データ: `w_av`（Weighted Career AV）
- `draft_picks.parquet` の `w_av` 列（Pro Football Reference 算出）
- **加重キャリアAV**：キャリア全体の AV（Approximate Value）を合計するが、
  **直近のシーズンほど高い重みをかけて集計**したもの
- 参考値：Tom Brady 184.0 / Peyton Manning 176.0 / Aaron Rodgers 169.0 / Drew Brees 167.0
- ドラフト指名なし選手（UDFA）は `draft_picks` に存在しないため `w_av = 0`

### recency_bonus（在籍の新しさ補正）
```
recency_bonus = 1.0 + 0.1 × max(0, last_season - 2015)
```
- `last_season`: rosters データにおける選手の最終出場シーズン
- 2015年以降も活躍している選手を優遇（例：2024年まで現役 → ×1.9）
- 2015年以前に引退した選手は補正なし（×1.0）

### 最終スコア
```
fame_score = w_av × recency_bonus
```
- `w_av = 0`（UDFA 等）の場合は `出場シーズン数 × 5` を代替値として使用

## Step 3: Criteria の列挙

ターゲット選手から以下 8 カテゴリの Criteria を自動抽出する。

| type | label 例 | データソース | 備考 |
|------|---------|------------|------|
| `college` | `College: Purdue` | roster の `college` 列 | 転校生（"Delaware; Pittsburgh"）は先頭の大学のみ使用 |
| `position` | `Position: TE` | roster の `position` 列 | 下記の除外リストに該当しないもののみ |
| `draft_year` | `Draft Class: 2001` | roster の `entry_year` 列 | |
| `draft_round` | `1st Round Pick (#3 Overall)` / `Draft Round: 2` | draft_picks の `round`（pfr_id で結合）| 1〜3ラウンドのみ。1巡の場合は `draft_pick_number` も付記 |
| `draft_club` | `Drafted by SD` | roster の `draft_club` 列（チーム移転を正規化）| |
| `team_played` | `Played for NO` | roster に登場した全チーム（各チーム1つ）| |
| `teammate` | `Teammates on NO (2006–2020)` | roster の年×チームをスパン化 | 下記ルール参照 |
| `award` | `Award: SBMVP` | `awardsdata/` フォルダの CSV 9種 | |

**賞のデータ（awardsdata/）**：MVP, OPoY, DPoY, ORoY, DRoY, CPoY, Heisman, SBMVP, WPMoY

**チーム移転の正規化**：`SD→LAC`, `STL→LA`, `OAK→LV`, `WSH→WAS`
- nflverse では年度によって `WAS` / `WSH` の両表記が混在するため `WSH` に統一

### position の除外リスト（`POSITION_EXCLUDED`）
選手目線でヒントとして役立たないポジションを除外する。

| 理由 | ポジション |
|------|-----------|
| 数が多く絞り込みにならない | QB, WR, RB |
| OL はラベルが多様 | OT, OG, T, G, OL |
| DB も数が多い | CB, S, SS, FS, DB |
| DL/LB は時代・チームで呼称が変わる | DE, DT, NT, DL, LB, OLB, ILB, MLB, EDGE |

→ 残るもの（K, P, LS, FB, TE, C 等）は Criteria として有効

### teammate criterion のルール

| 在籍パターン | 扱い |
|------------|------|
| 同チームに **2シーズン以上** | `Teammates on {team} ({開始年}–{終了年})` を生成（常に許可）|
| 同チームに **1シーズンのみ** かつ **SB優勝チーム** | `Teammates on {year} {team}` を生成（許可）|
| 同チームに **1シーズンのみ** で SB 未優勝 | 生成しない |

SB優勝チーム（`SUPERBOWL_CHAMPS`）：2010 GB〜2025 SEA の各年を定義済み

## Step 4: 有効な triple の条件

Criteria から3つを選ぶ際、以下の**両条件を満たす組み合わせのみ**を採用する。

### ルール1：`team_played` / `teammate` は triple 中に最大1つ

### ルール2：同チームを参照する criterion を2つ以上含まない（`draft_club` も含む）
- NG例：`Teammates on NYJ (2013–2017)` + `Drafted by NYJ` → 同チーム
- OK例：`Teammates on NYJ (2013–2017)` + `Drafted by SEA` → 別チーム

## Step 5: 一意性チェックと triple の選定

### 探索フロー

1. **フェーズ A（優先）**: `teammate` 1つ × 非チーム系 2つ の組み合わせを全列挙し、ランダムにシャッフルして最大 `MAX_COMBO_TRY` 件試行
2. **フェーズ B（フォールバック）**: 全 Criteria からの3択を `is_valid_combo` でフィルタしながら同様に試行

各試行で以下を確認：
- プール全体に対して「条件A ∩ 条件B ∩ 条件C」を計算
- 交差集合がターゲット選手1人のみ → 採用（`[UNIQUE]` タグ）
- 複数人いる場合 → 交差集合が最小のものを暫定ベストとして保持
- 一意が見つからない場合は暫定ベストを使用（`[BEST ~N]` タグで警告）

## Step 6: ヒント選手の選定（criterion 別優先順位）

各 criterion に対して、条件を満たす選手（ターゲット・既出ヒント選手を除く）から2人を選ぶ。

### criterion 別ソート基準

| criterion type | ソート基準 | 理由 |
|----------------|-----------|------|
| `college` | ターゲットの `entry_year` との差が小さい順、次いで `fame_score` 降順 | 同大学・同時期（同じドラフトクラス世代）の選手が自然な連想を生む |
| `draft_year` | draft pick番号（`draft_pick_number`）昇順 | 上位指名＝知名度が高い傾向 |
| `draft_round` | draft pick番号（`draft_pick_number`）昇順 | 1巡目は上位指名を優先して提示 |
| その他 | `fame_score` 降順 | 有名選手を優先 |

### 選定プロセス
1. ソートした全候補から上位 `HINT_TOP_POOL`（10人）を候補プールとして確定
2. その10人からランダムに2人を選択（毎回少し変化させるため）
3. `random.seed(42)` により再現性は保持

### ヒント選手の重複防止
- 3つの criterion をまたいで同じ選手が選ばれないよう、既出の選手を除外してから次の criterion の候補を絞る

### 補完処理
- 候補が2人未満の場合、pool 全体の `fame_score` 上位から未使用選手で補完

## Step 6.5: ヒント開示順の並べ替え（難易度ソート）

triple が確定した後、3つの criterion を **合致する選手数（`match_count`）の降順** でソートし、
`red → green → blue` の順に割り当てる。

- `red`（1ミス後に解除）: `match_count` 最大 = 最も曖昧なヒント（難しい）
- `green`（2ミス後に解除）: `match_count` 中程度
- `blue`（3ミス後に解除）: `match_count` 最小 = 最も絞り込まれたヒント（簡単）

**効果**: 最初のヒントは広い条件（例: College: Alabama）、最後のヒントは狭い条件（例: Award: SBMVP）になり、
後ろのヒントを見るほど確信を持って答えられるようになる。

## Step 7: 出力

### `src/data/puzzles/player_database.json`（全日共有）
- 約10,000人の選手名リスト（1ファイルのみ）
- フロントエンドが1回だけロードし、全日のパズルで共有する
- これにより各日の JSON が軽量になる（1日あたり数KB → 数MB の削減）

### `src/data/puzzles/day_{N}.json`（各日）

```json
{
  "id": "day_1",
  "date": "2026-04-05",
  "answer": {
    "name": "Drew Brees",
    "description": "",   // 手動で記入
    "comment": ""        // 手動で記入
  },
  "connections": {
    "red":   { "colorCode": "#ff6b6b", "hint": "Teammates on NO (2010–2021)", "players": ["Chase Daniel", "Terron Armstead"] },
    "green": { "colorCode": "#2ecc71", "hint": "Drafted by LAC",              "players": ["Eli Manning", "Justin Herbert"] },
    "blue":  { "colorCode": "#3498db", "hint": "Award: CPoY",                 "players": ["Ryan Tannehill", "Christian McCaffrey"] }
  }
}
```

- `playerDatabase` フィールドは含まない（`player_database.json` を参照）
- `description` / `comment` は空欄で出力され、出題者が手動で記入する
- `week_{date}.json` に同週7問分をまとめたファイルも出力

## フロントエンド対応（Next.js）

### 選手名の正規化（ファジーマッチング）
- `Jr.` / `Sr.` / `II` / `III` / `IV` などのサフィックスを除去して比較
- これにより "Odell Beckham Jr." と "Odell Beckham" の両方の入力を正解として受け付ける
- サジェスト検索・正解判定の両方に適用

### playerDatabase の分離ロード
- `page.tsx`（サーバーコンポーネント）で `player_database.json` を1回インポート
- `DailyNFLPuzzle` コンポーネントに `playerDatabase` prop として渡す
- 各日の puzzle JSON には含めない（型定義からも削除）

---

# 要件定義（元仕様）
1. **使用技術**: Python, `pandas`, `json`
2. **目的**: ゲームのフロントエンド（React/Next.js）で読み込めるJSONファイルを生成すること。
3. **出題候補プールの絞り込み（ノイズ除去）**:
   - スクリプト実行時に、最新のロースターデータや過去のデータをロードし、無名選手を弾くフィルターをかけます。
   - 例: 「2015年以降にプレイした選手」かつ「通算AV (Approximate Value) が〇〇以上」「通算試合数 が〇〇以上」などを基準とし、対象となる「プレイヤープール」を作成してください（条件は後で調整できるように変数化）。

# コアロジック（厳格な条件生成と一意性の担保）
以下のステップで処理を行う関数 `generate_daily_puzzle(target_player_name)` を作成してください。

## Step 1: ターゲット（正解選手）の特定
- 引数として渡された選手名（例: "Drew Brees"）のデータをプレイヤープールから取得します。
- この選手がパズルの中央の「？」になります。

## Step 2: 属性（Criteria）の抽出
ターゲット選手のデータから、明確な事実に基づく属性をリストアップします。
以下の厳格なルールに基づくカテゴリーを使用してください。他にも良いと思うカテゴリ分けがあったら提案してOK。：
- **Draft**: 指名年 (例: `Draft Class: 2001`), 指名ラウンド (例: `Draft Round: 2`), 指名巡と順位 (`Draft pick: 1`), 指名チーム (例: `Drafted by SD`)
- **College**: 出身大学 (例: `College: Purdue`)
- **Position**: ポジション (例: `Position: QB`)
- **Teams Played**: 1試合以上出場したチーム (例: `Played for NO`, `Played for SD`、チーム名がSDからLACなど変わるのには注意)
- **Awards**: 賞の獲得経験あり（例: `ORoY` これはNFLverseからおそらく取得できないので、awardsdataというフォルダに入れた。MVP,Offensive player of the year (OPoY), DPoY, ORoY, DRoY, CPoY, Heisman, Super bowl MVP (SBMVP), Walter Payton Man of the Year (WPMoY)のそれぞれのcsvが入っているのでそれを参照）
- **Teammates**: 以下の追加要件を参照
-
## 追加要件: チームメイト・リレーションの実装
「現在の所属」ではなく「過去の共通点」を重視するため、以下のロジックをPythonスクリプトに追加してください。

### 1. データの拡張
- `nfl_data_py.load_rosters()` から、過去10年分程度のロースターデータを読み込み、「選手ID」と「年度・チーム」の対応表を作成します。
- これにより、「選手Aと選手Bが、どの年に、どのチームで一緒だったか」を判定可能にします。

### 2. Criteria（条件）の新規カテゴリー
以下の条件を「一意性テスト」の候補に加えます。
- **Teammates (Pro)**: 特定の年・チームでのチームメイト。
  - 例: `Teammates on 2021 Rams` (正解選手がMatthew Staffordの場合、Cooper Kuppなどがヒント選手になる)
- **Teammates (College)**: 同じ大学の同時期の在籍者。
  - 例: `Teammates at LSU (2019)` (Joe BurrowとJa'Marr Chaseなど)
- **Shared Captains/Awards**: 同一年に同じチームでタイトルを獲った、などの関係性。


### 3. 一意性チェックの強化
「チームメイト」は母数が多いため、スクリプトは以下のフローでチェックを繰り返します。
1. 正解選手 X を選ぶ。
2. X の属性リスト（大学、ドラフト年、過去の所属チームなど）を作成。
3. 属性リストから3つをランダムに選択。そのうち1つ以上を「Teammates on [Year] [Team]」にする。
4. 全プレイヤープールに対して、その3条件を満たすのが X のみであることを確認する。
5. もし X 以外にも該当者がいる場合、3つの条件の組み合わせを変える（例：年度を絞る、別のチームメイト軸に変える）ことで、必ず1人に収束させる。

### 4. ヒント選手の選定アルゴリズム
- 条件が `Teammates on 2021 Rams` の場合、ヒント選手として選ぶ2名は、なるべく「その年を象徴する有名選手」を優先してピックアップするように重み付けしてください（`AV` スコアが高い順など）。

## Step 3: 一意性の検証（Intersection Test）
- Step 2で抽出した属性の中から、ランダムに3つ（例：A, B, C）を選びます。
- **重要**: プレイヤープール全体に対して、「条件A ∩ 条件B ∩ 条件C」をすべて満たす選手を検索します。
- 該当者が「ターゲット選手1人のみ」であれば、その3つの条件セットを採用します。
- 複数人該当した場合は破棄し、別の3つの組み合わせを試行してください。

## Step 4: ヒント選手（周辺選手）の抽出
- 採用された3つの条件（A, B, C）それぞれについて、プレイヤープールの中から該当する選手をターゲット以外から**2名ずつ**ランダムに選びます。
- これらが、アスタリスクの線の両端に配置される選手となります。

# 出力形式
最終的に、以下のフォーマットのJSONファイル（`day_X.json`）をエクスポートする機能をつけてください。
色の割り当て（Red, Green, BlueのHEXコード）もスクリプト内で付与してください。

```json
{
  "id": "day_1",
  "answer": {
    "name": "Drew Brees",
    "description": "Auto-generated short bio or stats",
    "comment": "出題者の一言（手動で編集可能な空欄、または自動生成）"
  },
  "connections": {
    "red": {
      "colorCode": "#ff6b6b",
      "hint": "College: Purdue",
      "players": ["George Karlaftis", "Raheem Mostert"]
    },
    "green": {
      "colorCode": "#2ecc71",
      "hint": "Played for NO",
      "players": ["Chris Olave", "Alvin Kamara"]
    },
    "blue": {
      "colorCode": "#3498db",
      "hint": "Position: QB",
      "players": ["Matthew Stafford", "Justin Herbert"]
    }
  }
}
```

## 実行フローの想定
自分が好きな選手（ターゲット）のリスト（例: ["Drew Brees", "Patrick Mahomes", "Aaron Donald"]）をループで回す。

それぞれの選手に対して上記ロジックを実行し、1週間分（7つ）のJSONファイルを一括で生成するメイン処理を書いてください。


