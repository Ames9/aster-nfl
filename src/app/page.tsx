import fs from "fs";
import path from "path";
import DailyNFLPuzzle from "@/components/DailyNFLPuzzle";
import type { PuzzleData, PlayerEntry } from "@/data/day1";

const PUZZLES_DIR = path.join(process.cwd(), "src/data/puzzles");

/**
 * src/data/puzzles/ にある day_N.json を全て読み込み、
 * 今日（JST）の日付に対応するパズルを返す。
 *
 * - 日付が完全一致するものを優先
 * - 一致しない場合は day_1 起点でローテーション
 * - 新しいパズルを追加しても page.tsx の変更は不要
 */
function getTodaysPuzzle(): { puzzle: PuzzleData; playerDatabase: PlayerEntry[] } {
  const today = new Date().toLocaleDateString("sv-SE", {
    timeZone: "Asia/Tokyo",
  });

  // day_N.json を番号順で読み込む
  const files = fs
    .readdirSync(PUZZLES_DIR)
    .filter((f) => /^day_\d+\.json$/.test(f))
    .sort((a, b) => {
      const na = parseInt(a.match(/\d+/)![0]);
      const nb = parseInt(b.match(/\d+/)![0]);
      return na - nb;
    });

  const puzzles: PuzzleData[] = files.map((f) =>
    JSON.parse(fs.readFileSync(path.join(PUZZLES_DIR, f), "utf-8"))
  );

  // playerDatabase を共有 JSON から読み込む
  const dbPath = path.join(PUZZLES_DIR, "player_database.json");
  const playerDatabase: PlayerEntry[] = fs.existsSync(dbPath)
    ? JSON.parse(fs.readFileSync(dbPath, "utf-8"))
    : [];

  // 日付完全一致
  const exact = puzzles.find((p) => p.date === today);
  if (exact) return { puzzle: exact, playerDatabase };

  // ローテーション（startDate 基準）
  if (puzzles.length === 0) {
    throw new Error("No puzzle files found in src/data/puzzles/");
  }
  const startDate = new Date(puzzles[0].date + "T00:00:00+09:00");
  const nowDate   = new Date(today + "T00:00:00+09:00");
  const dayOffset = Math.floor(
    (nowDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
  );
  const idx =
    ((dayOffset % puzzles.length) + puzzles.length) % puzzles.length;
  return { puzzle: puzzles[idx], playerDatabase };
}

export default function Home() {
  const { puzzle, playerDatabase } = getTodaysPuzzle();

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-black min-h-screen py-12 px-4 sm:px-6">
      <DailyNFLPuzzle
        data={puzzle}
        playerDatabase={playerDatabase}
        lang="ja"
      />
    </div>
  );
}
