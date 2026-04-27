import React from "react";
import { motion } from "framer-motion";
import type { PuzzleData } from "../../data/day1";

function extractCategory(hint: string): string {
  if (/teammate/i.test(hint)) return "NFL Teammate";
  if (/^College:/i.test(hint)) return "College";
  if (/^Draft Class:/i.test(hint)) return "Draft Class";
  if (/^Drafted by/i.test(hint)) return "Draft Pick";
  if (/^Award:/i.test(hint)) return "Award";
  if (/^Position:/i.test(hint)) return "Position";
  return "Connection";
}

type HintAreaProps = {
  mistakes: number;
  maxMistakes: number;
  connections: PuzzleData["connections"];
  texts: any;
};

export const HintArea: React.FC<HintAreaProps> = ({
  mistakes,
  maxMistakes,
  connections,
  texts
}) => {
  const hints = [
    { key: "red", label: "Red", data: connections.red, unlockAt: 1 },
    { key: "green", label: "Green", data: connections.green, unlockAt: 2 },
    { key: "blue", label: "Blue", data: connections.blue, unlockAt: 3 },
  ];

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
          {texts.hints}
        </h3>
        <div className="flex items-center gap-1">
          <span className="text-xs text-zinc-500 mr-2">{texts.remainingLives}:</span>
          {[...Array(maxMistakes)].map((_, i) => (
            <span
              key={i}
              className={`text-lg font-bold leading-none ${
                i < maxMistakes - mistakes
                  ? "text-white drop-shadow-[0_0_6px_rgba(255,255,255,0.7)]"
                  : "text-zinc-700"
              }`}
            >
              ✱
            </span>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        {hints.map((hint) => {
          const isUnlocked = mistakes >= hint.unlockAt;

          return (
            <div
              key={hint.key}
              className="relative overflow-hidden rounded-lg border bg-zinc-900"
              style={{
                borderColor: `${hint.data.colorCode}${isUnlocked ? "80" : "40"}`,
              }}
            >
              {/* colored left bar — always visible */}
              <div
                className="absolute left-0 top-0 bottom-0 w-1"
                style={{
                  backgroundColor: hint.data.colorCode,
                  opacity: isUnlocked ? 1 : 0.35,
                }}
              />

              <div className="p-3 pl-4">
                {isUnlocked ? (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col"
                  >
                    <span
                      className="text-xs font-bold mb-0.5"
                      style={{ color: hint.data.colorCode }}
                    >
                      {hint.label}:
                    </span>
                    <span className="text-sm text-zinc-200">{hint.data.hint}</span>
                  </motion.div>
                ) : (
                  <div className="flex flex-col">
                    <span
                      className="text-xs font-bold mb-0.5"
                      style={{ color: hint.data.colorCode }}
                    >
                      {hint.label}: {extractCategory(hint.data.hint)}
                    </span>
                    <span className="text-sm text-zinc-600">???</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
