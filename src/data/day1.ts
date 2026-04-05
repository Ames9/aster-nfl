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

export const day1Data: PuzzleData = {
  id: "day_1",
  date: "2026-04-05",
  answer: {
    name: "Drew Brees",
    description: "2000年代を代表する正確無比なパサー。Saintsに初のスーパーボウルをもたらした。",
    comment: "Purdue大出身のQBといえば彼ですね！"
  },
  connections: {
    red: {
      colorCode: "#ff6b6b",
      hint: "背番号9",
      players: ["Kenneth Walker III", "Matthew Stafford"]
    },
    green: {
      colorCode: "#2ecc71",
      hint: "New Orleans Saints 所属経験",
      players: ["Chris Olave", "Alvin Kamara"]
    },
    blue: {
      colorCode: "#3498db",
      hint: "Purdue大学 出身",
      players: ["George Karlaftis", "Raheem Mostert"]
    }
  }
};
