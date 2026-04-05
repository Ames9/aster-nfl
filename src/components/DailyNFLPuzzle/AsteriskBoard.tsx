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
    <div className="relative w-full aspect-square max-w-[400px] mx-auto flex items-center justify-center bg-zinc-900 rounded-xl overflow-hidden shadow-lg border border-zinc-800">
      <svg viewBox="0 0 400 400" className="w-full h-full">
        {/* Draw lines */}
        {lines.map((line, i) => {
          const rad = (line.angle * Math.PI) / 180;
          const x1 = cx + Math.cos(rad) * lineLength;
          const y1 = cy + Math.sin(rad) * lineLength;
          
          const radOpposite = ((line.angle + 180) * Math.PI) / 180;
          const x2 = cx + Math.cos(radOpposite) * lineLength;
          const y2 = cy + Math.sin(radOpposite) * lineLength;

          return (
            <g key={line.key}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={line.color}
                strokeWidth={4}
                strokeLinecap="round"
                className="opacity-70"
              />
            </g>
          );
        })}

        {/* Draw text */}
        {lines.map((line, i) => {
          const rad1 = (line.angle * Math.PI) / 180;
          const tx1 = cx + Math.cos(rad1) * radius;
          const ty1 = cy + Math.sin(rad1) * radius;

          const rad2 = ((line.angle + 180) * Math.PI) / 180;
          const tx2 = cx + Math.cos(rad2) * radius;
          const ty2 = cy + Math.sin(rad2) * radius;

          return (
            <g key={`text-${line.key}`}>
              <foreignObject x={tx1 - 60} y={ty1 - 20} width="120" height="40" className="overflow-visible">
                <div className="flex items-center justify-center w-full h-full text-center">
                  <span className="text-xs font-semibold text-white bg-zinc-900/80 px-2 py-0.5 rounded border border-zinc-700 backdrop-blur-sm"
                        style={{ borderColor: `${line.color}40` }}>
                    {line.players[0]}
                  </span>
                </div>
              </foreignObject>
              <foreignObject x={tx2 - 60} y={ty2 - 20} width="120" height="40" className="overflow-visible">
                <div className="flex items-center justify-center w-full h-full text-center">
                  <span className="text-xs font-semibold text-white bg-zinc-900/80 px-2 py-0.5 rounded border border-zinc-700 backdrop-blur-sm"
                        style={{ borderColor: `${line.color}40` }}>
                    {line.players[1]}
                  </span>
                </div>
              </foreignObject>
            </g>
          );
        })}

        {/* Center node */}
        <foreignObject x={cx - 50} y={cy - 50} width="100" height="100">
          <div className="flex items-center justify-center w-full h-full">
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
        </foreignObject>
      </svg>
    </div>
  );
};
