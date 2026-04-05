import React from "react";
import { motion } from "framer-motion";
import type { PuzzleData } from "../../data/day1";

type AsteriskBoardProps = {
  data: PuzzleData["connections"];
  gameState: "playing" | "clear" | "gameover";
  correctAnswerText?: string;
  isCorrect?: boolean;
};

export const AsteriskBoard: React.FC<AsteriskBoardProps> = ({
  data,
  gameState,
  correctAnswerText,
  isCorrect
}) => {
  // SVG drawing configuration
  const cx = 200;
  const cy = 200;
  const lineLength = 150; // length from center
  const radius = 170; // text placement radius

  const lines = [
    { key: "red", color: data.red.colorCode, angle: 90, players: data.red.players },
    { key: "green", color: data.green.colorCode, angle: 210, players: data.green.players },
    { key: "blue", color: data.blue.colorCode, angle: 330, players: data.blue.players },
  ];

  return (
    <div className="relative w-full aspect-square max-w-[400px] mx-auto bg-zinc-900 rounded-xl shadow-lg border border-zinc-800">
      {/* SVG for lines only — no foreignObject to avoid mobile rendering bugs */}
      <svg viewBox="0 0 400 400" className="absolute inset-0 w-full h-full">
        {lines.map((line) => {
          const rad = (line.angle * Math.PI) / 180;
          const x1 = cx + Math.cos(rad) * lineLength;
          const y1 = cy + Math.sin(rad) * lineLength;

          const radOpposite = ((line.angle + 180) * Math.PI) / 180;
          const x2 = cx + Math.cos(radOpposite) * lineLength;
          const y2 = cy + Math.sin(radOpposite) * lineLength;

          return (
            <line
              key={line.key}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={line.color}
              strokeWidth={4}
              strokeLinecap="round"
              className="opacity-70"
            />
          );
        })}
      </svg>

      {/* Player name labels — absolutely positioned HTML elements aligned to SVG coordinates */}
      {lines.map((line) => {
        const rad1 = (line.angle * Math.PI) / 180;
        const tx1 = cx + Math.cos(rad1) * radius;
        const ty1 = cy + Math.sin(rad1) * radius;

        const rad2 = ((line.angle + 180) * Math.PI) / 180;
        const tx2 = cx + Math.cos(rad2) * radius;
        const ty2 = cy + Math.sin(rad2) * radius;

        return (
          <React.Fragment key={`label-${line.key}`}>
            <div
              className="absolute flex items-center justify-center pointer-events-none"
              style={{
                left: `${(tx1 / 400) * 100}%`,
                top: `${(ty1 / 400) * 100}%`,
                transform: "translate(-50%, -50%)",
              }}
            >
              <span
                className="text-xs font-semibold text-white bg-zinc-900/80 px-2 py-0.5 rounded border border-zinc-700 backdrop-blur-sm whitespace-nowrap"
                style={{ borderColor: `${line.color}40` }}
              >
                {line.players[0]}
              </span>
            </div>
            <div
              className="absolute flex items-center justify-center pointer-events-none"
              style={{
                left: `${(tx2 / 400) * 100}%`,
                top: `${(ty2 / 400) * 100}%`,
                transform: "translate(-50%, -50%)",
              }}
            >
              <span
                className="text-xs font-semibold text-white bg-zinc-900/80 px-2 py-0.5 rounded border border-zinc-700 backdrop-blur-sm whitespace-nowrap"
                style={{ borderColor: `${line.color}40` }}
              >
                {line.players[1]}
              </span>
            </div>
          </React.Fragment>
        );
      })}

      {/* Center node — absolutely centered, no longer depends on foreignObject */}
      <div
        className="absolute flex items-center justify-center"
        style={{
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
        }}
      >
        {gameState === "playing" ? (
          <motion.div
            className="w-16 h-16 bg-zinc-800 rounded-full border-2 border-zinc-600 flex items-center justify-center shadow-lg"
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ repeat: Infinity, duration: 2 }}
          >
            <span className="text-2xl font-bold text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]">?</span>
          </motion.div>
        ) : (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className={`w-24 h-24 rounded-full flex items-center justify-center text-center shadow-2xl p-2 ${
              isCorrect
                ? "bg-zinc-800 border-2 border-white drop-shadow-[0_0_16px_rgba(255,255,255,0.9)]"
                : "bg-zinc-800 border-2 border-zinc-600"
            }`}
          >
            <span className="text-sm font-bold text-white leading-tight">
              {correctAnswerText}
            </span>
          </motion.div>
        )}
      </div>
    </div>
  );
};
