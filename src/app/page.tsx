import fs from "fs";
import path from "path";
import PuzzleNavigator from "./PuzzleNavigator";
import type { PuzzleData, PlayerEntry } from "@/data/day1";

export const dynamic = "force-dynamic";

const PUZZLES_DIR = path.join(process.cwd(), "src/data/puzzles");

function loadPuzzles(): PuzzleData[] {
  const files = fs
    .readdirSync(PUZZLES_DIR)
    .filter((f) => /^day_\d+\.json$/.test(f))
    .sort((a, b) => parseInt(a.match(/\d+/)![0]) - parseInt(b.match(/\d+/)![0]));
  return files.map((f) =>
    JSON.parse(fs.readFileSync(path.join(PUZZLES_DIR, f), "utf-8"))
  );
}

/** 今日（JST）のパズルインデックス（0始まり）を返す */
function getTodayIndex(puzzles: PuzzleData[]): number {
  const today = new Date().toLocaleDateString("sv-SE", {
    timeZone: "Asia/Tokyo",
  });

  const exact = puzzles.findIndex((p) => p.date === today);
  if (exact >= 0) return exact;

  if (puzzles.length === 0) return 0;
  const startDate = new Date(puzzles[0].date + "T00:00:00+09:00");
  const nowDate   = new Date(today        + "T00:00:00+09:00");
  const dayOffset = Math.floor(
    (nowDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
  );
  return ((dayOffset % puzzles.length) + puzzles.length) % puzzles.length;
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ day?: string }>;
}) {
  const { day } = await searchParams;

  const puzzles = loadPuzzles();
  const todayIndex = getTodayIndex(puzzles);

  // ?day=N （1始まり）で過去日を指定。未指定・範囲外は今日
  let currentIndex = todayIndex;
  if (day !== undefined) {
    const n = parseInt(day, 10);
    if (!isNaN(n) && n >= 1 && n <= puzzles.length) {
      // 未来日（n-1 > todayIndex）は今日にフォールバック
      currentIndex = Math.min(n - 1, todayIndex);
    }
  }

  const puzzle = puzzles[currentIndex];

  const dbPath = path.join(PUZZLES_DIR, "player_database.json");
  const playerDatabase: PlayerEntry[] = fs.existsSync(dbPath)
    ? JSON.parse(fs.readFileSync(dbPath, "utf-8"))
    : [];

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-black min-h-screen py-12 px-4 sm:px-6">
      <PuzzleNavigator
        puzzle={puzzle}
        playerDatabase={playerDatabase}
        dayNumber={currentIndex + 1}
        todayNumber={todayIndex + 1}
        lang="ja"
      />
    </div>
  );
}
