"""全画面ボタンのテスト。
使い方: python tests/fullscreen.py   （先に npm run build。合成データを使う）
- iphone: Fullscreen API を消した状態（iPhone の Safari 相当）→ 画面いっぱいの重ね表示になること
- android: Fullscreen API あり → 本物の全画面になること
どちらも 縦(390x844)で開く → 横(844x390)に回す → グラフが画面の幅・高さいっぱいに描き直されること → 閉じると元に戻ること
スクショは tests/out/fs_*.png
"""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mock  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "out"
PAGES = {"list": ("demo/index.html", ".ch-fig", ".ch-chart svg"), "compare": ("demo/compare.html", ".c-figwrap", ".c-fig svg")}
NO_FS = "delete Element.prototype.requestFullscreen; delete Element.prototype.webkitRequestFullscreen;"

STATE = """([wrap, svg]) => { const w = document.querySelector('[data-tool] ' + wrap), s = document.querySelector('[data-tool] ' + svg);
  const r = w.getBoundingClientRect(), sr = s.getBoundingClientRect(), hint = w.querySelector('.ct-fshint');
  return { full: w.classList.contains('ct-full'), fsApi: !!document.fullscreenElement, wrapW: Math.round(r.width), wrapH: Math.round(r.height),
    svgW: Math.round(sr.width), svgH: Math.round(sr.height), svgBottom: Math.round(sr.bottom), hint: getComputedStyle(hint).display !== 'none',
    btn: w.querySelector('.ct-fs').textContent, vw: innerWidth, vh: innerHeight, scrollLock: document.documentElement.classList.contains('ct-noscroll') }; }"""


async def main():
    OUT.mkdir(exist_ok=True)
    ok = True
    async with async_playwright() as p:
        b = await mock.launch(p)
        for dev in ("iphone", "android"):
            for tab, (page, wrap, svg) in PAGES.items():
                ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
                pg = await ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                if dev == "iphone":
                    await pg.add_init_script(NO_FS)
                await mock.install(pg)
                await pg.goto((ROOT / page).as_uri())
                await pg.wait_for_selector("[data-tool] tbody tr")
                arg = [wrap, svg]
                before = await pg.evaluate(STATE, arg)
                await pg.locator("[data-tool] .ct-fs").first.tap()
                await pg.wait_for_timeout(400)
                port = await pg.evaluate(STATE, arg)
                await pg.screenshot(path=str(OUT / f"fs_{dev}_{tab}_portrait.png"))
                await pg.set_viewport_size({"width": 844, "height": 390})
                await pg.wait_for_timeout(500)
                land = await pg.evaluate(STATE, arg)
                await pg.screenshot(path=str(OUT / f"fs_{dev}_{tab}_landscape.png"))
                await pg.locator("[data-tool] .ct-fs").first.tap()
                await pg.wait_for_timeout(400)
                after = await pg.evaluate(STATE, arg)
                checks = {
                    "閉じている": not before["full"] and before["btn"].endswith("全画面"),
                    "開いた": port["full"] and port["btn"].endswith("閉じる") and port["scrollLock"],
                    "全画面の方式": port["fsApi"] == (dev == "android"),
                    "縦で案内が出る": port["hint"],
                    "横で案内が消える": not land["hint"],
                    "横で幅いっぱい": land["svgW"] >= land["vw"] - 40,
                    "横で高さが画面内": land["svgBottom"] <= land["vh"] + 2 and land["svgH"] >= 200,
                    "閉じたら戻る": not after["full"] and not after["fsApi"] and not after["scrollLock"] and after["svgH"] >= 400 and after["btn"].endswith("全画面"),
                    "エラーなし": not errs,
                }
                bad = [k for k, v in checks.items() if not v]
                print(f"{dev} {tab}: {'OK' if not bad else 'NG ' + ','.join(bad)}  縦={port['svgW']}x{port['svgH']} 横={land['svgW']}x{land['svgH']} (画面 {land['vw']}x{land['vh']}) {errs[:1]}")
                ok = ok and not bad
                await ctx.close()
        await b.close()
    print("FULLSCREEN OK" if ok else "FULLSCREEN NG")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
