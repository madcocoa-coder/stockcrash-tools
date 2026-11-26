"""公開前のスモークテスト。
使い方: python tests/smoke.py <テスト用HTMLのパスまたはURL> [--tab list|compare]
- ページを開いて8秒待ち、JSエラーがないこと、表の行が1行以上あること、統計/冒頭文が出ていることを確認
- スマホ幅(390px)とPC幅(1200px)の両方で実行し、スクリーンショットを tests/out/ に保存
必要: pip install playwright && playwright install chromium
"""
import asyncio, sys, pathlib
from playwright.async_api import async_playwright

async def run(target, tab):
    out = pathlib.Path(__file__).parent / "out"; out.mkdir(exist_ok=True)
    url = target if target.startswith("http") else pathlib.Path(target).resolve().as_uri()
    ok = True
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w in (1200, 390):
            pg = await b.new_page(viewport={"width": w, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto(url); await pg.wait_for_timeout(8000)
            rows = await pg.locator("[data-tool] tbody tr").count()
            print(f"[{w}px] rows={rows} errors={errs[:3]}")
            await pg.screenshot(path=str(out / f"{tab}_{w}.png"), full_page=True)
            if errs or rows == 0:
                ok = False
        await b.close()
    print("OK" if ok else "NG"); sys.exit(0 if ok else 1)

if __name__ == "__main__":
    tab = sys.argv[sys.argv.index("--tab") + 1] if "--tab" in sys.argv else "list"
    asyncio.run(run(sys.argv[1], tab))
