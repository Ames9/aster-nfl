"use client";

import { useRouter } from "next/navigation";
import DailyNFLPuzzle from "@/components/DailyNFLPuzzle";
import type { PuzzleData, PlayerEntry } from "@/data/day1";

type Props = {
  puzzle: PuzzleData;
  playerDatabase: PlayerEntry[];
  dayNumber: number;
  todayNumber: number;
  lang?: "en" | "ja";
};

export default function PuzzleNavigator({
  puzzle,
  playerDatabase,
  dayNumber,
  todayNumber,
  lang = "ja",
}: Props) {
  const router = useRouter();

  const goToDay = (n: number) => {
    if (n === todayNumber) {
      router.push("/");
    } else {
      router.push(`/?day=${n}`);
    }
  };

  const isToday = dayNumber === todayNumber;

  return (
    <div className="w-full flex flex-col items-center gap-3">
      {/* 過去日閲覧中のバナー */}
      {!isToday && (
        <div className="flex items-center gap-3 text-sm bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2">
          <span className="text-zinc-400">Day {dayNumber} を表示中</span>
          <button
            onClick={() => goToDay(todayNumber)}
            className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
          >
            今日へ →
          </button>
        </div>
      )}

      {/* key=puzzle.id でデイ変更時に state をリセット */}
      <DailyNFLPuzzle
        key={puzzle.id}
        data={puzzle}
        playerDatabase={playerDatabase}
        lang={lang}
        onPrevDay={dayNumber > 1 ? () => goToDay(dayNumber - 1) : undefined}
        onNextDay={dayNumber < todayNumber ? () => goToDay(dayNumber + 1) : undefined}
      />
    </div>
  );
}
