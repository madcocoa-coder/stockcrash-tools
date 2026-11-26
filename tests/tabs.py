"""タブ統合（v1.1.0）の確認。合成データ（tests/fixtures）で動かす。
使い方: python tests/tabs.py   （先に npm run build）
- 一覧ページ（data-tab=list）: 一覧タブが開き、比較タブはまだ読み込まれていない
- 1928年以降の暴落の行をタップ →「重ねて比較で見る」ボタン → 比較タブに切り替わり、その暴落がチップに入る
- 1927年以前（月次）の暴落ではボタンが出ない
- 一覧タブに戻ると選択が残っている
- 比較ページ（data-tab=compare）と、共有URL（#cmp=…）で開いた一覧ページは比較タブから開く
PC幅・スマホ幅の両方
"""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mock  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(__file__).parent / "out"


async def open_page(b, page, w, hash_=""):
    pg = await b.new_page(viewport={"width": w, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await mock.install(pg)
    await pg.goto((ROOT / "demo" / page).as_uri() + hash_)
    await pg.wait_for_timeout(1200)
    return pg, errs


async def state(pg):
    return await pg.evaluate("""() => ({
      tab: [...document.querySelectorAll('.ct-tabs button')].filter(b => b.classList.contains('on')).map(b => b.dataset.t)[0],
      listShown: !document.querySelector('.ct-pane[data-p=list]').hidden,
      cmpShown: !document.querySelector('.ct-pane[data-p=compare]').hidden,
      cmpMounted: !!document.querySelector('.ct-pane[data-p=compare] .cmp-root'),
      chips: [...document.querySelectorAll('.c-chips .chip')].map(c => c.textContent.replace('×','').trim()),
      lead: (document.querySelector('.c-lead') || {}).textContent || '',
      act: (document.querySelector('.ch-act') || {}).textContent || '',
      sel: (document.querySelector('.ch-root tbody tr.sel td') || {}).textContent || '',
    })""")


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
            pg, errs = await open_page(b, "index.html", w)
            s = await state(pg)
            check("一覧ページは一覧タブで開く", s["tab"] == "list" and s["listShown"] and not s["cmpShown"], s)
            check("比較タブはまだ読み込まない", not s["cmpMounted"], s)
            # 月次（1927年以前）の行: ボタンなし
            await pg.evaluate("() => { const tr = [...document.querySelectorAll('.ch-root tbody tr')].find(r => /18\\d\\d年\\d+月$/.test(r.children[2].textContent)); tr.click(); }")
            await pg.wait_for_timeout(200)
            s = await state(pg)
            check("1927年以前の暴落ではボタンを出さない", s["act"] == "", s)
            # 日次（1928年以降）の行: ボタン → 比較タブ
            name = await pg.evaluate("() => { const tr = [...document.querySelectorAll('.ch-root tbody tr')].find(r => /\\d+月\\d+日$/.test(r.children[2].textContent) && !/未回復/.test(r.textContent)); tr.click(); return tr.children[0].textContent; }")
            await pg.wait_for_timeout(200)
            s = await state(pg)
            check("1928年以降の暴落ではボタンを出す", "重ねて比較" in s["act"], s)
            await pg.click(".ch-tocmp")
            await pg.wait_for_timeout(1200)
            s = await state(pg)
            check("ボタンで比較タブに切り替わる", s["tab"] == "compare" and s["cmpShown"] and not s["listShown"], s)
            check("選んだ暴落がチップに入る", len(s["chips"]) >= 2 and any(c.split(" ")[-1] in name for c in s["chips"]), (name, s["chips"]))
            await pg.screenshot(path=str(OUT / f"tabs_compare_{w}.png"), full_page=True)
            await pg.click(".ct-tabs button[data-t=list]")
            await pg.wait_for_timeout(300)
            s = await state(pg)
            check("一覧タブに戻ると選択が残る", s["tab"] == "list" and s["sel"] != "", s)
            check("エラーなし（一覧ページ）", not errs, errs)
            await pg.close()

            pg, errs = await open_page(b, "compare.html", w)
            s = await state(pg)
            check("比較ページは比較タブで開く", s["tab"] == "compare" and s["cmpShown"] and len(s["chips"]) > 0, s)
            await pg.click(".ct-tabs button[data-t=list]")
            await pg.wait_for_timeout(800)
            rows = await pg.locator(".ch-root tbody tr").count()
            check("比較ページから一覧タブも開ける", rows > 0, rows)
            check("エラーなし（比較ページ）", not errs, errs)
            await pg.close()

            pg, errs = await open_page(b, "index.html", w, "#cmp=C070,C072")
            s = await state(pg)
            check("共有URL（#cmp=）は一覧ページでも比較タブで開く", s["tab"] == "compare", s)
            await pg.close()
        await b.close()
    print("TABS OK" if ok else "TABS NG")
    sys.exit(0 if ok else 1)


asyncio.run(main())
