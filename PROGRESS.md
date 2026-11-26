# 作業の経過

## 2026-11-26 要望: スマホ用の全画面表示ボタン
- 一覧・比較のグラフの右上に「⛶ 全画面」ボタン。押すとグラフ周り（一覧: チャート＋凡例＋詳細枠／比較: 表示期間＋チャート＋読み取り行）を画面いっぱいに出す。「✕ 閉じる」・戻る・Esc で戻る
- Android・PC は本物の全画面。Android は横向き固定も試す（端末が許せば）。iPhone の Safari は要素の全画面に非対応なので、画面いっぱいの重ね表示で代わりにする（背面のスクロールは止める）
- 縦向きのスマホでは「スマホを横向きにすると大きく見られます」を出す。横にすると幅・高さいっぱいに描き直す（390x844 → 844x390 で、一覧 820x266・比較 810x255）
- テスト: `tests/fullscreen.py`（iPhone相当・Android相当 × 一覧・比較）OK。parity.py はボタンの行を隠して legacy と一致のまま。wp_sim.py OK
- 実機（iPhone・Android）での確認はまだ。WordPress のテーマのヘッダーなどが重ね表示の上に出ないかも実機で見る

## 2026-11-26 第1段階（外部化と部品化）: 実装と突き合わせまで完了・公開前の確認が残り

### やったこと
- `src/` に core / series / ui / views / main / styles を作り、legacy の2ツールを部品に分けて書き直した（構成は CLAUDE.md）
- esbuild でビルド → `dist/crash-tools.min.js`（約27KB、CSS込み）。`demo/index.html`（一覧）・`demo/compare.html`（比較）
- この作業環境からは Googleシート・本番ページ・jsDelivr に接続できなかった（ネットワーク許可は見送り）。そのため
  - `tests/fixtures/` に**合成データ**（シートと同じ列構成。本物の株価ではない）を作り、
  - `tests/mock.py` で gviz へのリクエストを合成データで差し替えてテストした

### 確認結果（合成データ）
- `tests/parity.py`: legacy と統合版を同じデータ・同じ操作で開いて突き合わせ → **一致**
  - 一覧 39状態（対象×期間の12通り、全列の並び替え昇順・降順、絞り込み、行・帯のタップ）
  - 比較 18状態（表示期間5通り、グラフのタップ、追加・上限超え・削除、主な暴落に戻す、今回に近い下落を探す）＋共有URL `#cmp=`
  - 比べたもの: 統計タイル、表の全行、チャートSVG、詳細枠、自動文、チップ、追加メニュー、読み取り行。最後の状態のスクショも画素一致
  - PC幅 1200px・スマホ幅 390px の両方。6回連続で OK
- 既知差分1件: legacy の一覧は **1970年1月の月次の点を落としていた**（`if(d&&v>0)` で、1970-01-01 は `Date.UTC` が 0 なので偽扱い）。統合版は描く。parity.py はこの差だけ許容（増えた点の位置が1970-01-01かを目盛りから逆算して確認）
- `tests/smoke.py --mock`: 一覧・比較とも PC幅・スマホ幅 OK
- `tests/wp_sim.py`: WP QUADS の広告差し込み（`</p>` の後に `<script>` 入り広告）、`&`→`&#038;`、強めのテーマCSS を再現したページで、エラーなし・ボタンや表の見た目がテーマに負けない → OK
  - テーマの `svg{max-width:…}` に負けないよう、svg に `max-width:none` を足した（legacy にはない。通常の表示は変わらない）

### 残り（公開まで）
1. **本物のシートで突き合わせ**: docs.google.com に接続できる環境で `python3 tests/parity.py --live` と `python3 tests/smoke.py demo/index.html --tab list` / `demo/compare.html --tab compare`
2. **本番相当テスト**: 本番ページのHTMLを取得 → 埋め込み部分（legacy の div#ch-root / div#cmp-root 一式）を統合版の埋め込みに差し替え → `<base href="https://gomi-investor.com/">` を入れてローカルで開き、広告入りでエラーがないこと（gomi-investor.com への接続が必要）
3. **タグ配信**: ブランチを main に取り込んだ後、`v1.0.0` タグを付けて push → `https://cdn.jsdelivr.net/gh/madcocoa-coder/stockcrash-tools@v1.0.0/dist/crash-tools.min.js` が返ることを確認
4. ユーザーに WordPress の埋め込み差し替えを依頼（CLAUDE.md の「埋め込み」）。一覧ページは `data-tab="list"`、比較ページは `data-tab="compare"`

1〜2 は、この環境のネットワーク許可（docs.google.com, gomi-investor.com, cdn.jsdelivr.net）か、ユーザーの手元（Windows の Claude Code）で実行する。
