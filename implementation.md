実装計画
「NFL Convergence」 — NFLデイリーパズルゲームを新規 Next.js プロジェクトとして構築します。

技術スタック
Next.js (App Router) + TypeScript
Tailwind CSS （plan.md 指定）
Framer Motion （アニメーション）
主なコンポーネント設計
コンポーネント	役割
DailyNFLPuzzle/index.tsx	メイン状態管理・use client
AsteriskBoard.tsx	SVGアスタリスク描画（3本線・6選手名）
PlayerInput.tsx	サジェスト付き入力フォーム
HintArea.tsx	ライフ・ヒントカード表示
ResultModal.tsx	結果モーダル（SNSシェア機能）
i18n.ts	日英UIテキスト定数
確認事項
IMPORTANT

プロジェクトを Aster_NFL/ ディレクトリ内に直接 create-next-app で初期化します。既存の plan.md は保持します。
<DailyNFLPuzzle data={day1Data} /> として親ページから呼び出せる独立コンポーネント設計
既存の Next.js サイトに組み込む想定で、app/page.tsx はデモ用として作成
この計画で問題なければ実装を開始します。



NFL Convergence — 実装計画
概要
plan.md に基づき、NFLの選手名を当てるデイリーパズル「NFL Convergence」を実装します。 アスタリスク型（＊型）のビジュアルで6名のヒント選手から中央の正解選手を当てるゲームです。

技術スタック
項目	選択
フレームワーク	Next.js (App Router)
スタイリング	Tailwind CSS
アニメーション	Framer Motion
言語	TypeScript
提案する構成
Aster_NFL/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── src/
│   ├── app/
│   │   ├── layout.tsx       # ルートレイアウト
│   │   ├── page.tsx         # デモページ (コンポーネントを埋め込む)
│   │   └── globals.css
│   ├── components/
│   │   └── DailyNFLPuzzle/
│   │       ├── index.tsx            # メインコンポーネント（use client）
│   │       ├── AsteriskBoard.tsx    # SVGアスタリスク描画
│   │       ├── PlayerInput.tsx      # サジェスト付き入力フォーム
│   │       ├── HintArea.tsx         # ヒント・ステータスエリア
│   │       ├── ResultModal.tsx      # ゲーム終了モーダル
│   │       └── i18n.ts              # UIテキスト定数（日英対応）
│   └── data/
│       └── day1.ts                  # モックデータ (day_1)
実装ステップ
Step 1: Next.jsプロジェクト初期化
npx create-next-app@latest でセットアップ（TypeScript + Tailwind + App Router）
Framer Motion インストール
Step 2: データ型・モックデータ定義
PuzzleData 型定義
day1.ts にplan.mdのモックデータを実装
Step 3: i18n定数ファイル
i18n.ts に日英テキストを定数オブジェクトとして定義
Step 4: AsteriskBoard コンポーネント
SVGで3本の線（60度間隔）を描画
中央の「？」円
6箇所のヒント選手名（水平テキスト）
各色（Red/Green/Blue）に応じた色分け
Step 5: PlayerInput コンポーネント
テキスト入力＋オートコンプリートドロップダウン
playerDatabase から候補をフィルタリング
Step 6: HintArea コンポーネント
残りライフ表示（ハートアイコンなど）
各色のヒントカード（初期はロック状態）
Step 7: ResultModal コンポーネント
クリア / ゲームオーバー表示
正解選手プロフィール
SNSシェアボタン（Wordleスタイル絵文字）
Step 8: DailyNFLPuzzle メインコンポーネント
状態管理（回答履歴、ライフ、ゲーム状態）
ミス時のヒント開示ロジック
Framer Motionによるアニメーション
Step 9: デモページ組み込み
app/page.tsx に <DailyNFLPuzzle data={day1Data} /> を埋め込み
デザイン詳細
背景色: #18181b
Red: #ff6b6b, Green: #2ecc71, Blue: #3498db
アスタリスク: 3本の線が 0°, 60°, 120° の角度で交差
フォント: Google Fonts (Inter または Outfit)
ダークモードベース、ネオン/サイバー雰囲気
検証計画
npm run dev でローカル動作確認
ブラウザで全ゲームフロー（正解・3回不正解）を動作確認
モバイルビューポートでのレスポンシブ確認

