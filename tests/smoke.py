"""公開前のスモークテスト。
使い方: python tests/smoke.py <テスト用HTMLのパスまたはURL> [--tab list|compare] [--mock]
- ページを開いて8秒待ち、JSエラーがないこと、表の行が1行以上あること、統計/冒頭文が出ていることを確認
- スマホ幅(390px)とPC幅(1200px)の両方で実行し、スクリーンショットを tests/out/ に保存
- --mock: Googleシートへのリクエストを tests/fixtures の合成データで差し替える（ネットにつながらない環境用）
必要: pip install playwright && playwright install chromium（入らない環境は CHROMIUM_PATH でブラウザを指定）
"""
import asyncio, sys, pathlib
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mock  # noqa: E402

CHECK = {  # タブごとに「中身が出ているか」を見る要素
    "list": "[data-tool] .ch-stats .ch-stat",
    "compare": "[data-tool] .c-lead",
}


async def run(target, tab, use_mock):
    out = pathlib.Path(__file__).parent / "out"; out.mkdir(exist_ok=True)
    if not target.startswith("http") and not use_mock:
        mock.serve()  # file:// だと gviz が CORS で断るので http で配る
    url = target if target.startswith("http") else mock.url_for(target)
    ok = True
    async with async_playwright() as p:
        b = await mock.launch(p)
        for w in (1200, 390):
            pg = await b.new_page(viewport={"width": w, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            if use_mock:
                await mock.install(pg)
            await pg.goto(url); await pg.wait_for_timeout(8000)
            rows = await pg.locator("[data-tool] tbody tr").count()
            filled = await pg.locator(CHECK[tab]).count()
            lead = (await pg.locator(CHECK[tab]).first.inner_text()) if filled else ""
            bad = "読み込み中" in lead or "読み込めません" in lead
            print(f"[{w}px] rows={rows} filled={filled} errors={errs[:3]}" + (f" lead={lead[:40]!r}" if bad else ""))
            await pg.screenshot(path=str(out / f"{tab}_{w}.png"), full_page=True)
            if errs or rows == 0 or not filled or bad:
                ok = False
        await b.close()
    print("OK" if ok else "NG"); sys.exit(0 if ok else 1)

if __name__ == "__main__":
    tab = sys.argv[sys.argv.index("--tab") + 1] if "--tab" in sys.argv else "list"
    asyncio.run(run(sys.argv[1], tab, "--mock" in sys.argv))
