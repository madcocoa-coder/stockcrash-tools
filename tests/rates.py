"""金利を重ねる（v1.2.0）の確認。合成の株価データ＋本物の金利（tests/fixtures/rates.csv）で動かす。
使い方: python tests/rates.py   （先に npm run build）
- 一覧: 「金利を重ねる」で米10年金利 → 右目盛・線・利上げ局面の帯・凡例・注意書き。詳細枠に金利の変化。政策金利に切り替え・なしに戻す
- 比較: 「金利の変化も表に出す」→ 表に2列（米10年金利・政策金利）。グラフをタップすると見出しの日数が変わる。隠すと元の列数
PC幅・スマホ幅
"""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mock  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(__file__).parent / "out"


async def main():
    OUT.mkdir(exist_ok=True)
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(("OK " if cond else "NG ") + name + ("" if cond else f"  {info}"))
        ok = ok and cond

    async with async_playwright() as p:
        b = await mock.launch(p)
        for w in (1200, 390):
            print(f"--- {w}px")
            pg = await b.new_page(viewport={"width": w, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await mock.install(pg)
            await pg.goto((ROOT / "demo" / "index.html").as_uri())
            await pg.wait_for_timeout(1200)
            base = await pg.evaluate("() => document.querySelectorAll('.ch-chart path').length")
            await pg.click(".ch-seg[data-k=rate] button[data-v=ust10y]")
            await pg.wait_for_timeout(800)
            s = await pg.evaluate("""() => ({
              paths: [...document.querySelectorAll('.ch-chart path')].map(p => p.getAttribute('stroke')),
              pct: [...document.querySelectorAll('.ch-chart text')].filter(t => /%$/.test(t.textContent)).length,
              hikes: [...document.querySelectorAll('.ch-chart rect')].filter(r => r.getAttribute('fill') == '#6b4fa0').length,
              leg: document.querySelector('.ch-leg2').textContent })""")
            check("米10年金利の線", "#1a8c80" in s["paths"] and len(s["paths"]) == base + 1, s["paths"])
            check("右目盛（%）", s["pct"] >= 3, s["pct"])
            check("利上げ局面の帯", s["hikes"] >= 5, s["hikes"])
            check("凡例と注意書き", "米10年金利" in s["leg"] and "利上げ局面" in s["leg"] and "関係なく" in s["leg"], s["leg"])
            await pg.evaluate("() => { const tr = [...document.querySelectorAll('.ch-root tbody tr')].find(r => /\\d{4}年\\d+月\\d+日$/.test(r.children[2].textContent) && r.children[2].textContent >= '1960'); tr.click(); }")
            await pg.wait_for_timeout(300)
            inf = await pg.inner_text(".ch-info")
            check("詳細枠に金利の変化", "米10年金利" in inf and "pt" in inf, inf)
            await pg.screenshot(path=str(OUT / f"rates_list_{w}.png"), full_page=True)
            await pg.click(".ch-seg[data-k=rate] button[data-v=ff]")
            await pg.wait_for_timeout(300)
            st = await pg.evaluate("() => [...document.querySelectorAll('.ch-chart path')].map(p => p.getAttribute('stroke'))")
            check("政策金利に切り替え", "#6b4fa0" in st, st)
            await pg.click(".ch-seg[data-k=rate] button[data-v=none]")
            await pg.wait_for_timeout(300)
            s2 = await pg.evaluate("() => ({ n: document.querySelectorAll('.ch-chart path').length, leg: document.querySelector('.ch-leg2').innerHTML, inf: document.querySelector('.ch-info').textContent })")
            check("なしに戻すと元どおり", s2["n"] == base and s2["leg"] == "" and "米10年金利" not in s2["inf"], s2)

            # 比較
            await pg.click(".ct-tabs button[data-t=compare]")
            await pg.wait_for_timeout(1500)
            n0 = await pg.locator(".cmp-root thead th").count()
            await pg.click(".c-ratebtn")
            await pg.wait_for_timeout(800)
            h = await pg.evaluate("() => [...document.querySelectorAll('.cmp-root thead th')].map(t => t.textContent)")
            check("比較の表に金利の2列", len(h) == n0 + 2 and "米10年金利" in h[-2] and "政策金利" in h[-1], h)
            cells = await pg.evaluate("() => [...document.querySelectorAll('.cmp-root tbody tr')].map(r => r.lastElementChild.textContent)")
            check("金利の変化の値", any("pt" in c for c in cells), cells)
            sv = await pg.query_selector(".c-fig svg"); bb = await sv.bounding_box()
            await pg.mouse.click(bb["x"] + bb["width"] * 0.6, bb["y"] + bb["height"] / 2)
            await pg.wait_for_timeout(300)
            h2 = await pg.evaluate("() => document.querySelector('.cmp-root thead th.c-rateh').textContent")
            check("タップした日数が見出しに出る", "日目" in h2, h2)
            await pg.screenshot(path=str(OUT / f"rates_compare_{w}.png"), full_page=True)
            await pg.click(".c-ratebtn")
            await pg.wait_for_timeout(300)
            check("隠すと元の列数", await pg.locator(".cmp-root thead th").count() == n0)
            check("エラーなし", not errs, errs)
            await pg.close()
        await b.close()
    print("RATES OK" if ok else "RATES NG")
    sys.exit(0 if ok else 1)


asyncio.run(main())
