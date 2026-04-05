"""
generate_comments.py
既存の puzzle JSON に Claude API でコメントを追記するスタンドアロンスクリプト。

Usage:
    ANTHROPIC_API_KEY=sk-... python3 generate_comments.py
    ANTHROPIC_API_KEY=sk-... python3 generate_comments.py --days 1-7
    ANTHROPIC_API_KEY=sk-... python3 generate_comments.py --days 1,3,5
"""

import json
import os
import sys
import argparse
from pathlib import Path

PUZZLES_DIR = Path("src/data/puzzles")

def generate_comment(player_name: str, connections: dict, client) -> str:
    hints = [conn["hint"] for conn in connections.values()]
    hints_str = " / ".join(hints)

    prompt = f"""あなたはNFLが大好きな日本人ファンです。
以下の選手について、パズルゲームの出題者として添える「ひとことコメント」を日本語で書いてください。

選手名: {player_name}
ヒント（共通点）: {hints_str}

条件:
- 1〜2文、50〜100字程度
- 「〜な選手ですね」「〜が印象的でした」のようなカジュアルで親しみやすいトーン
- 正解（選手名）は書かない
- 受賞・所属・ポジションなどの事実を盛り込みつつ、感想っぽく
- 出力はコメント本文だけ（前置き・説明不要）"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def parse_days(spec: str, total: int) -> list[int]:
    """'1-7' や '1,3,5' を [1,3,5,6,7] のようなリストに変換"""
    result = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            result.extend(range(int(a), int(b) + 1))
        else:
            result.append(int(part))
    return sorted(set(n for n in result if 1 <= n <= total))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", default=None, help="対象日のレンジ（例: 1-7 または 1,3,5）。省略時は全ファイル対象")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY が設定されていません。")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # 対象ファイルを収集
    all_files = sorted(PUZZLES_DIR.glob("day_*.json"))
    if not all_files:
        print("ERROR: src/data/puzzles/day_*.json が見つかりません。")
        sys.exit(1)

    if args.days:
        day_nums = parse_days(args.days, len(all_files))
        target_files = [PUZZLES_DIR / f"day_{n}.json" for n in day_nums]
    else:
        target_files = all_files

    print(f"対象: {len(target_files)} ファイル\n")

    for path in target_files:
        if not path.exists():
            print(f"  [SKIP] {path.name} not found")
            continue

        with open(path, encoding="utf-8") as f:
            puzzle = json.load(f)

        player = puzzle["answer"]["name"]
        existing = puzzle["answer"].get("comment", "")

        if existing:
            print(f"  [SKIP] {path.name} – {player} (コメントあり: {existing[:30]}...)")
            continue

        print(f"  [{path.name}] {player} – コメント生成中...")
        try:
            comment = generate_comment(player, puzzle["connections"], client)
            puzzle["answer"]["comment"] = comment
            # description フィールドが残っていれば削除
            puzzle["answer"].pop("description", None)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(puzzle, f, ensure_ascii=False, indent=2)
            print(f"    → {comment}")
        except Exception as e:
            print(f"    [ERROR] {e}")

    print("\n完了!")


if __name__ == "__main__":
    main()
