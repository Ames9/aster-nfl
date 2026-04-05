/** playerDatabase の1エントリ。同名異ポジション選手を区別するために pos を持つ */
export type PlayerEntry = {
  name: string;
  pos?: string;
};

export type HintConnection = {
  colorCode: string;
  hint: string;
  players: [string, string];
};

export type PlayerAnswer = {
  name: string;
  comment: string;        // 出題者のひとことコメント（手動記入）
  photo_url?: string;     // Wikipedia サムネイル URL
  photo_credit?: string;  // 出典（例: "Wikipedia – https://..."）CC BY-SA
  pfr_id?: string;
  pfr_url?: string;
  espn_id?: string;
  espn_url?: string;
};

export type PuzzleData = {
  id: string;
  date: string; // "YYYY-MM-DD"
  answer: PlayerAnswer;
  connections: {
    red: HintConnection;
    green: HintConnection;
    blue: HintConnection;
  };
  // playerDatabase は player_database.json から別途ロードし、コンポーネントに渡す
};

