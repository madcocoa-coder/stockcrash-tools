"""WordPress 本番の壊れ方を再現したページで統合版を開くテスト（本番ページを取得できない環境用の代わり）。
使い方: python tests/wp_sim.py   （先に npm run build）
再現するもの:
- WP QUADS:「段落の後に広告」が、本文中の文字列 `</p>` の後ろに <script> 入りの広告HTMLを差し込む
- wptexturize: 本文の `&` を `&#038;` に変える
- テーマのCSS: button / table / th / td / select / svg / input に強めの装飾
確認すること: JSエラーなし・一覧と比較の両方が描ける・ボタンや表の見た目がテーマに負けていない
本番ページそのもので確かめる手順は PROGRESS.md の「本番相当テスト」を参照
"""
import asyncio, pathlib, re, sys
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mock  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "out"
SHEET = "1JP-4PJimOphXB9pTvG8xCW4F12Jn5FrnHVUiT4iRVFM"
JS = (ROOT / "dist" / "crash-tools.min.js").as_uri()

THEME = """<style>
.entry-content button,#main button{background:#e91e63;color:#fff;padding:20px 40px;border-radius:30px;font-size:22px}
#main table{border:3px solid #000;font-size:20px} #main th{background:#333;color:#fff;text-align:center} #main td{padding:20px;text-align:center}
#main select{width:50%;height:60px} #main svg{max-width:200px} #main input{border:4px solid red;width:100%}
.entry-content p{margin:0 0 2em;font-size:18px}
</style>"""
AD = '<div class="quads-location"><script>window.__ads=(window.__ads||0)+1;</script><ins class="adsbygoogle">AD</ins></div>'


def post(tab):
    # 本文（WordPressの埋め込みブロックそのまま）。段落の後に広告を入れる
    body = f"""<p>米国株（S&P500）の暴落の歴史を一覧にしました。</p>
<div data-tool="crash" data-tab="{tab}" data-sheet="{SHEET}"></div>
<script src="{JS}" defer></script>
<p>データは毎週更新します。Q&A は記事の最後に。</p>"""
    body = body.replace("&", "&#038;")  # wptexturize
    body = body.replace("</p>", "</p>" + AD)  # WP QUADS
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{THEME}</head>
<body><main id="main"><article class="entry-content">{body}</article></main></body></html>"""


STYLE_CHECK = """() => { const q = s => document.querySelector(s), cs = e => e && getComputedStyle(e);
  const b = q('[data-tool] .ch-seg button, [data-tool] .seg button'), th = q('[data-tool] th'), sv = q('[data-tool] svg');
  return { btnBg: cs(b).backgroundColor, btnPad: cs(b).padding, btnFont: cs(b).fontSize, thBg: cs(th).backgroundColor, svgW: sv && sv.getBoundingClientRect().width,
           ads: window.__ads || 0 }; }"""


async def main():
    OUT.mkdir(exist_ok=True)
    ok = True
    async with async_playwright() as p:
        b = await mock.launch(p)
        for tab in ("list", "compare"):
            f = OUT / f"wp_sim_{tab}.html"
            f.write_text(post(tab), encoding="utf-8")
            for w in (1200, 390):
                pg = await b.new_page(viewport={"width": w, "height": 1000})
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                await mock.install(pg)
                await pg.goto(f.as_uri())
                await pg.wait_for_selector("[data-tool] tbody tr", timeout=10000)
                await pg.wait_for_timeout(300)
                s = await pg.evaluate(STYLE_CHECK)
                await pg.screenshot(path=str(OUT / f"wp_sim_{tab}_{w}.png"), full_page=True)
                good = (not errs and s["ads"] == 2 and s["btnPad"] == "5px 11px" and s["btnFont"] == "13px" and s["btnBg"] in ("rgb(255, 255, 255)", "rgb(35, 59, 94)", "rgb(20, 22, 26)")
                        and s["thBg"] == "rgb(236, 238, 241)" and s["svgW"] > 250)
                print(f"{tab} @{w}px: errors={errs[:2]} {s} {'OK' if good else 'NG'}")
                ok = ok and good
                await pg.close()
        await b.close()
    print("WP SIM OK" if ok else "WP SIM NG")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
