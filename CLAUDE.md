# stockcrash-tools の仕組み

ブログ（gomi-investor.com）の「米国株（S&P500）の暴落の歴史（一覧）」と「暴落比較ツール」を1本のJSにまとめ、GitHub＋jsDelivr から配信する。
経緯と段階の計画は `HANDOFF.md`、作業の経過は `PROGRESS.md`。返答は日本語・カジュアル・端的に。

## 構成

```
src/
  core/format.js     日付・期間・%の整形、シートの値の読み取り（legacy と同じ出力）
  core/data.js       gviz の URL、取得（URL単位でページ内キャッシュ）、CSV解析、見出し名で列を探す
  core/events.js     「暴落一覧」タブ → 暴落の配列（派生値: dd, bear, mon, on, fall, rec, tot）、短い名前
  series/registry.js 系列の定義と読み込み（loadSeries(sheet, def, 'monthly'|'daily', [from,to]?)）
  series/sp500.js    S&P500 の取得元（月次・日次タブ）
  series/ust10y.js   米10年金利、series/fedfunds.js 政策金利（タブ「金利_月次」gid 536414932。registry に valueAt・hikes（利上げ局面））
  ui/chart.js        SVG 文字列の部品（el, pathD, yGrid, xGrid, logTicks, steps, onResize）
  ui/controls.js     セグメント、チップ
  ui/fullscreen.js   全画面ボタン（Fullscreen API＋Android は横向き固定。使えない iPhone は position:fixed の重ね表示）
  views/list.js      一覧ビュー（mountList）
  views/compare.js   比較ビュー（mountCompare）
  main.js            [data-tool="crash"] を探して「暴落の一覧」「重ねて比較」の2タブを載せる（v1.1.0）。data-tab は最初に開くタブ、#cmp= があれば比較から。
                     2つ目のタブは初めて開いたときに読み込む。一覧の「この暴落を『重ねて比較』で見る」→ 比較タブへ切り替えて add(id)。CSS を <style id="crash-tools-css"> で1回だけ入れる
  styles.css         ルート配下にスコープ。:is(#crash-tools,[data-tool]) で id 1個分の詳細度にしてテーマCSSに負けないようにしている
build.mjs            esbuild。CSS は minify して文字列としてJSに埋め込む → dist/crash-tools.min.js（コミットする）
demo/                index.html（一覧）・compare.html（比較）。WordPress と同じマークアップ
tests/
  fixtures/          合成データ（本物の株価ではない）と生成スクリプト
  mock.py            gviz へのリクエストを合成データで差し替える・Date.now 固定・ブラウザ起動
  parity.py          legacy と統合版を同じデータ・同じ操作で開き、HTMLとスクショを突き合わせる
  smoke.py           ページを開いてエラーなし・表が出ることを確認（PC幅・スマホ幅）
  wp_sim.py          WP QUADS の広告差し込み・& の変換・テーマCSSを再現したページで確認
  fullscreen.py      全画面ボタン（iPhone相当・Android相当 × 縦→横に回転 → 閉じる）
  prod_sim.py        本番ページの埋め込み（legacy でも公開中の統合版でも）を手元のビルドに差し替えて、本番のテーマ・広告込みで開く（要ネット）
  tabs.py            タブ統合（一覧→比較へ送る、比較ページ、共有URL）
  rates.py           金利を重ねる（一覧の線・帯・凡例、比較の表の列）。fixtures/rates.csv は本物の金利
legacy/              現行の埋め込み版（比較の基準。消さない）
scripts/crash_update.py  週次更新スクリプト（claude.ai のスケジュールタスクが sha256 で照合して実行）。金利も FRED から更新（v1.2.0〜）
scripts/trigger_prompt.md  スケジュールタスクの指示文（スクリプト本体と sha256 入り）。直したら作り直してタスクに貼る
```

## 埋め込み（WordPress に貼るのはこれだけ）

```html
<div data-tool="crash" data-tab="list" data-sheet="1JP-4PJimOphXB9pTvG8xCW4F12Jn5FrnHVUiT4iRVFM"></div>
<script src="https://cdn.jsdelivr.net/gh/madcocoa-coder/stockcrash-tools@v1.2.0/dist/crash-tools.min.js" defer></script>
```
- `data-tab` は `list` か `compare`（最初に開くタブ。どちらのページでも両方のタブが使える）。`data-sheet` を省くと既定のシート
- バージョンはタグで固定。`@latest` やブランチ指定は使わない

## コマンド

```
npm install                 # esbuild だけ
npm run build               # dist/crash-tools.min.js（--dev で minify なしの dist/crash-tools.js、こちらはコミットしない）
python3 tests/parity.py     # legacy と突き合わせ（--live で本物のシート）
python3 tests/smoke.py demo/index.html --mock --tab list
python3 tests/smoke.py demo/compare.html --mock --tab compare
python3 tests/wp_sim.py
python3 tests/fullscreen.py
python3 tests/tabs.py
python3 tests/rates.py
python3 tests/prod_sim.py   # 本番相当（gomi-investor.com・docs.google.com に接続できる環境で）
npm run fixtures            # 合成データを作り直す（固定シードなので同じものができる）
```
- Python の Playwright が同梱ブラウザを見つけられない環境では `CHROMIUM_PATH` を指定（なければ /opt/pw-browsers/chromium を自動で試す）
- テストの出力（スクショ・差分）は tests/out/（gitignore）
- 本物のシートを読むテスト（parity --live、smoke の --mock なし、prod_sim）は、リポジトリを http://127.0.0.1 で配って開く。file:// だとオリジンが null になり gviz が CORS で断るため

## 守ること

- データの定義・見出し名は変えない（HANDOFF.md 2.3）。列は見出し名で探す
- 見た目と数値は legacy と同じに保つ。変えるときは parity.py の既知差分に理由つきで足す
- 既知差分: legacy の一覧は 1970-01-01 の月次の点を落とす（`Date.UTC(1970,0,1)` が 0 で偽扱い）。統合版は描く
- 追加機能（legacy にない）: タブ（.ct-tabs）と「比較へ送る」ボタン（.ch-act、1928年以降の日次の暴落だけ）。parity.py では隠して比べる
- テーマ（Magazine Pro）は b・strong などに Raleway などを当てるので、ツール内は `*{font-family:inherit}` で全部そろえる（v1.1.0）
- 追加機能（legacy にない）: 全画面ボタン。範囲は一覧が .ch-fig（チャート＋凡例＋詳細枠）、比較が .c-figwrap（表示期間＋チャート＋読み取り行）。
  全画面中だけグラフの高さを画面に合わせる。parity.py ではボタンの行（.ct-fsbar）を隠して比べる
- 表示ラベル: 20%以上の下落は「暴落」、10〜20%は「調整」（v1.0.2 でユーザー決定。旧「弱気相場／弱気」）。データの定義と内部の名前（bear など）は変えていない。parity.py は legacy に同じ置き換え（LEGACY_LABELS）を当てて比べる
- 文字はツール内でシステムフォント・等幅数字に固定（styles.css 冒頭）。日本語フォントを先頭に置き、数字と漢字を同じフォントで描く（欧文フォントが先だと「82」と「回」で太さがずれる）。Windows はメイリオ優先。テーマの Web フォントは使わない（分割配信で太字の字形が一部だけ届き、ちぐはぐになったため。v1.0.1）。parity.py は legacy に同じ指定を足して比べる
- 全画面の高さ（fitHeight）は、枠の余白と子要素の上下マージンまで引く。一覧の詳細枠は全画面中だけ2行分の高さを確保（帯をタップして2行になっても下が切れない）
- WordPress 側に置くのは div と script src だけ。本文に `<p>` や `&` を含むインラインJSを書かない（WP QUADS / wptexturize で壊れる）
- `scripts/crash_update.py` を直したら claude.ai 側のスケジュールタスクの指示文（本体と sha256）も更新が必要。ユーザーに依頼する
- 系列を足すときは `src/series/` に定義を1つ作り registry に登録する
- 追加機能（legacy にない）: 金利（v1.2.0）。既定はオフ。一覧は「金利を重ねる」（.ch-rategrp）で米10年金利／政策金利の線（右目盛）と利上げ局面の帯（政策金利が1%pt以上上がった期間、3か月未満は除く、開始は谷の水準+0.25pt以内を最後に出た月）。
  比較は「金利の変化も表に出す」（.c-ratebtn）で表に2列。金利は選んだときに初めて読む。parity.py では隠して比べる
- 金利と株価の関係は断定しない（注意書き .ch-ratenote）。急な利上げの後の暴落もあれば、金利上昇と株高が並んだ時期、金利と無関係な暴落もある
- 金利のデータ: 米10年金利は1953-03まで Shiller の Long Interest Rate、1953-04から FRED GS10（月平均）。政策金利は FRED FEDFUNDS（1954-07〜）
- FRED は User-Agent がブラウザを名乗ると接続を切る。curl の UA で取る
