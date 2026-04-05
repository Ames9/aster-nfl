import React, { useState, useRef, useEffect } from "react";
import { Search } from "lucide-react";
import type { PlayerEntry } from "@/data/day1";

type PlayerInputProps = {
  disabled: boolean;
  playerDatabase: PlayerEntry[];
  onSubmit: (playerName: string) => void;
  placeholder: string;
  submitText: string;
  noResultsText: string;
};

export const PlayerInput: React.FC<PlayerInputProps> = ({
  disabled,
  playerDatabase,
  onSubmit,
  placeholder,
  submitText,
  noResultsText
}) => {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Jr. / Sr. / II / III / IV などのサフィックスを除去して比較
  const normalizeName = (s: string) =>
    s.toLowerCase().replace(/\s+(jr\.?|sr\.?|ii|iii|iv|v)$/i, "").trim();

  const normalizedQuery = normalizeName(query);
  const filteredPlayers = playerDatabase
    .filter(p => normalizeName(p.name).includes(normalizedQuery))
    .slice(0, 8);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query) return;
    onSubmit(query);
    setQuery("");
    setIsOpen(false);
  };

  // ドロップダウンから選択: 入力欄には name のみセット（pos は表示専用）
  const handleSelect = (entry: PlayerEntry) => {
    setQuery(entry.name);
    setIsOpen(false);
  };

  return (
    <div className="w-full mt-2" ref={wrapperRef}>
      <form onSubmit={handleSubmit} className="flex gap-2 relative">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            className="w-full bg-zinc-800 border border-zinc-700 text-white rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            placeholder={placeholder}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            disabled={disabled}
          />

          {isOpen && query && !disabled && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-50 overflow-hidden">
              {filteredPlayers.length > 0 ? (
                <ul>
                  {filteredPlayers.map(player => (
                    <li
                      key={`${player.name}__${player.pos ?? ""}`}
                      className="flex items-center gap-2 px-4 py-2 hover:bg-zinc-700 cursor-pointer text-sm text-zinc-200"
                      onClick={() => handleSelect(player)}
                    >
                      <span>{player.name}</span>
                      {player.pos && (
                        <span className="text-xs text-zinc-500 bg-zinc-900 px-1.5 py-0.5 rounded">
                          {player.pos}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="px-4 py-3 text-sm text-zinc-500">
                  {noResultsText}
                </div>
              )}
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={disabled || !query}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white font-semibold py-3 px-6 rounded-lg transition-colors whitespace-nowrap"
        >
          {submitText}
        </button>
      </form>
    </div>
  );
};
