"""本番相当テスト: 本番ページのHTMLを取得し、legacy の埋め込みを統合版に差し替えてローカルで開く。
使い方: python tests/prod_sim.py [ページURL]   （先に npm run build。gomi-investor.com と docs.google.com に接続できる環境で）
- 本番ページ内の legacy 埋め込み（div#ch-root または div#cmp-root の一式）を、統合版の <div data-tool="crash" ...> に置き換える
- 一覧タブ・比較タブの2通りを作り、<base href> で本番のCSS・広告（WP QUADS）を読み込んだ状態で開く
- 合格: 表の行が出る／統合版のスクリプトに起因するエラーがない。PC幅・スマホ幅
"""
import asyncio, pathlib, re, sys, urllib.request
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mock  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(__file__).parent / "out"
URL = next((a for a in sys.argv[1:] if a.startswith("http")),
           "https://gomi-investor.com/%e6%a0%aa%e5%bc%8f%e5%b8%82%e5%a0%b4-%e6%9a%b4%e8%90%bd%e3%81%ae%e6%ad%b4%e5%8f%b2%ef%bc%88sp500%ef%bc%89/")
SHEET = "1JP-4PJimOphXB9pTvG8xCW4F12Jn5FrnHVUiT4iRVFM"


def legacy_span(html):
    """legacy 埋め込みの開始と終了の位置。どちらのツールも最後は '})();\\n</script>\\n</div>' で閉じる"""
    m = re.search(r'<div id="(ch-root|cmp-root)"', html)
    if not m:
        raise SystemExit("legacy の埋め込みがページに見つからない")
    end = html.index("</script>", html.index("})();", m.start()))
    end = html.index("</div>", end) + len("</div>")
    return m.start(), end


async def main():
    OUT.mkdir(exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    a, b = legacy_span(html)
    base = mock.serve()
    js = mock.url_for(ROOT / "dist" / "crash-tools.min.js")
    ok = True
    async with async_playwright() as p:
        br = await mock.launch(p)
        for tab in ("list", "compare"):
            embed = f'<div data-tool="crash" data-tab="{tab}" data-sheet="{SHEET}"></div>\n<script src="{js}" defer></script>'
            page = html[:a] + embed + html[b:]
            page = page.replace("<head>", '<head><base href="https://gomi-investor.com/">', 1)
            f = OUT / f"prod_sim_{tab}.html"
            f.write_text(page, encoding="utf-8")
            for w in (1200, 390):
                pg = await br.new_page(viewport={"width": w, "height": 1000})
                errs = []
                pg.on("pageerror", lambda e: errs.append(f"{e}\n{getattr(e, 'stack', '') or ''}"))
                await pg.goto(mock.url_for(f), wait_until="domcontentloaded")
                await pg.wait_for_timeout(9000)
                rows = await pg.locator("[data-tool] tbody tr").count()
                ours = [e for e in errs if "crash-tools" in e]
                await pg.locator("[data-tool]").screenshot(path=str(OUT / f"prod_sim_{tab}_{w}.png"))
                print(f"{tab} @{w}px: rows={rows} errors(ours)={ours[:2]} errors(other)={len(errs) - len(ours)}")
                if rows == 0 or ours:
                    ok = False
                await pg.close()
        await br.close()
    print("OK" if ok else "NG")
    sys.exit(0 if ok else 1)


asyncio.run(main())
