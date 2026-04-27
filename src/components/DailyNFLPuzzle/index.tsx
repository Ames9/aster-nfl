"use client";

import React, { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { AsteriskBoard } from "./AsteriskBoard";
import { PlayerInput } from "./PlayerInput";
import { HintArea } from "./HintArea";
import { ResultModal } from "./ResultModal";
import { texts } from "./i18n";
import type { PuzzleData, PlayerEntry } from "../../data/day1";

type DailyNFLPuzzleProps = {
  data: PuzzleData;
  playerDatabase: PlayerEntry[];
  lang?: "en" | "ja";
  onPrevDay?: () => void;
  onNextDay?: () => void;
};

// Jr. / Sr. / II / III / IV などのサフィックスを除去して正規化
// 例: "Kenneth Walker III" → "kenneth walker"
function normalizeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+(jr\.?|sr\.?|ii|iii|iv|v)$/i, "")
    .trim();
}

export const DailyNFLPuzzle: React.FC<DailyNFLPuzzleProps> = ({
  data,
  playerDatabase,
  lang = "ja",
  onPrevDay,
  onNextDay,
}) => {
  const [gameState, setGameState] = useState<"playing" | "clear" | "gameover">("playing");
  const [mistakes, setMistakes] = useState(0);
  const maxMistakes = 4;
  const t = texts[lang];

  const handleGuess = (playerName: string) => {
    if (gameState !== "playing") return;

    // サフィックスを除去して比較（"Baker Mayfield" = "baker mayfield"）
    const isCorrect = normalizeName(playerName) === normalizeName(data.answer.name);

    if (isCorrect) {
      setMistakes(maxMistakes); // unlock all hints
      setGameState("clear");
    } else {
      const newMistakes = mistakes + 1;
      setMistakes(newMistakes);
      if (newMistakes >= maxMistakes) {
        setGameState("gameover");
      }
    }
  };

  // スキップ = ミス1回消費してヒントを開く
  const handleSkip = () => {
    if (gameState !== "playing") return;
    const newMistakes = mistakes + 1;
    setMistakes(newMistakes);
    if (newMistakes >= maxMistakes) {
      setGameState("gameover");
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4 md:p-6 bg-[#18181b] text-zinc-100 font-sans rounded-2xl shadow-2xl">
      {/* Header */}
      <header className="flex justify-between items-start mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base md:text-lg font-bold text-white tracking-wide">
              {t.title}
            </h1>
            <div className="flex items-center gap-1">
              {onPrevDay && (
                <button
                  onClick={onPrevDay}
                  className="w-5 h-5 flex items-center justify-center text-zinc-500 hover:text-zinc-200 transition-colors"
                  aria-label="Previous day"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
              <span className="text-sm font-mono text-zinc-400">{data.date}</span>
              {onNextDay && (
                <button
                  onClick={onNextDay}
                  className="w-5 h-5 flex items-center justify-center text-zinc-500 hover:text-zinc-200 transition-colors"
                  aria-label="Next day"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
          <p className="text-xs text-zinc-400 mt-1 leading-relaxed">{t.description}</p>
        </div>
      </header>

      {/* ゲーム中: 2カラム（ボード左 / ヒント+入力右）
          ゲーム終了後: 2カラム（ボード左 / ヒント右）+ フル幅の結果カード */}
      <div className="flex flex-col md:flex-row gap-6">
        {/* Left: Asterisk board */}
        <div className="flex-shrink-0 md:w-[380px]">
          <AsteriskBoard
            data={data.connections}
            gameState={gameState}
            correctAnswerText={gameState !== "playing" ? data.answer.name : undefined}
            isCorrect={gameState === "clear"}
          />
        </div>

        {/* Right: Hints + Input（プレイ中のみ） */}
        <div className="flex flex-col gap-4 flex-1 min-w-0">
          <HintArea
            mistakes={mistakes}
            maxMistakes={maxMistakes}
            connections={data.connections}
            texts={t}
          />

          {gameState === "playing" && (
            <div className="flex flex-col gap-2">
              <PlayerInput
                disabled={false}
                playerDatabase={playerDatabase}
                onSubmit={handleGuess}
                placeholder={t.placeholder}
                submitText={t.submit}
                noResultsText={t.noResults}
              />
              {/* スキップ：ミス1回消費して次のヒントを開く（全ヒント開放後はゲームオーバーへ） */}
              <button
                onClick={handleSkip}
                className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors text-center py-1"
              >
                {t.skip}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ゲーム終了後: フル幅の結果カード */}
      {gameState !== "playing" && (
        <div className="mt-6">
          <ResultModal
            isClear={gameState === "clear"}
            texts={t}
            answer={data.answer}
          />
        </div>
      )}

      {/* Footer: data source */}
      <p className="text-center text-[10px] text-zinc-700 mt-4">
        {t.dataSource}
      </p>
    </div>
  );
};

export default DailyNFLPuzzle;
