import React from "react";
import { motion } from "framer-motion";
import { CheckCircle, XCircle, ExternalLink } from "lucide-react";

type ResultModalProps = {
  isClear: boolean;
  texts: any;
  answer?: {
    name: string;
    comment?: string;
    photo_url?: string;
    photo_credit?: string;
    pfr_url?: string;
    espn_url?: string;
  };
};

export const ResultModal: React.FC<ResultModalProps> = ({ isClear, texts, answer }) => {
  const hasPhoto = !!answer?.photo_url;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-zinc-900 border border-zinc-700 rounded-xl overflow-hidden shadow-2xl"
    >
      {/* 写真あり: 横並び（写真左 / テキスト右） */}
      {hasPhoto ? (
        <div className="flex flex-col sm:flex-row">
          {/* 写真（全体がWikipediaへのリンク） */}
          <a
            href={answer?.photo_credit?.replace(/^Wikipedia – /, "") ?? "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="relative sm:w-56 flex-shrink-0 block group"
            title="Wikipedia で見る"
          >
            <img
              src={answer!.photo_url}
              alt={answer!.name}
              className="w-full h-48 sm:h-full object-cover object-top group-hover:brightness-90 transition-[filter]"
            />
            {/* 出典表示（CC BY-SA 義務） */}
            <span className="absolute bottom-1 right-1 text-[9px] text-white/60 group-hover:text-white/90 bg-black/50 px-1.5 py-0.5 rounded">
              Wikipedia ↗
            </span>
          </a>

          {/* テキスト・リンク */}
          <div className="flex flex-col justify-center p-5 gap-3 flex-1">
            <div className="flex items-center gap-2">
              {isClear
                ? <CheckCircle className="w-6 h-6 text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.7)]" />
                : <XCircle className="w-6 h-6 text-zinc-400" />}
              <h2 className={`text-xl font-bold ${isClear ? "text-white" : "text-zinc-300"}`}>
                {isClear ? texts.clear : texts.gameOver}
              </h2>
            </div>

            {answer?.comment && (
              <p className="text-sm text-zinc-400 leading-relaxed">
                {answer.comment}
              </p>
            )}

            {isClear && (answer?.pfr_url || answer?.espn_url) && (
              <div className="flex gap-2 flex-wrap">
                {answer.pfr_url && (
                  <a
                    href={answer.pfr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white border border-zinc-700 hover:border-zinc-500 rounded-lg px-3 py-1.5 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    {texts.viewOnPfr}
                  </a>
                )}
                {answer.espn_url && (
                  <a
                    href={answer.espn_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white border border-zinc-700 hover:border-zinc-500 rounded-lg px-3 py-1.5 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    {texts.viewOnEspn}
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* 写真なし: 縦並び中央揃え */
        <div className="p-5 text-center">
          <div className="flex justify-center mb-2">
            {isClear
              ? <CheckCircle className="w-10 h-10 text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.7)]" />
              : <XCircle className="w-10 h-10 text-zinc-400" />}
          </div>

          <h2 className={`text-xl font-bold ${isClear ? "text-white" : "text-zinc-300"}`}>
            {isClear ? texts.clear : texts.gameOver}
          </h2>

          {answer?.comment && (
            <p className="mt-3 text-sm text-zinc-400 leading-relaxed">
              {answer.comment}
            </p>
          )}

          {isClear && (answer?.pfr_url || answer?.espn_url) && (
            <div className="flex justify-center gap-3 mt-4">
              {answer.pfr_url && (
                <a
                  href={answer.pfr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white border border-zinc-700 hover:border-zinc-500 rounded-lg px-3 py-1.5 transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  {texts.viewOnPfr}
                </a>
              )}
              {answer.espn_url && (
                <a
                  href={answer.espn_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white border border-zinc-700 hover:border-zinc-500 rounded-lg px-3 py-1.5 transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  {texts.viewOnEspn}
                </a>
              )}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};
