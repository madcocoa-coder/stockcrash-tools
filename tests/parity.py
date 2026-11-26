"""legacy（現行の埋め込み版）と統合版を、同じ合成データ・同じ操作で開いて中身を突き合わせる。
使い方: python tests/parity.py [--live]   （先に npm run build）
- 既定は tests/fixtures の合成データ。--live なら本物のGoogleシートを読む（docs.google.com に接続できる環境で）
- 一覧: 対象×期間の全12通り、並び替え全列（昇順・降順）、名称の絞り込み、行・帯のタップ
- 比較: 既定の選択、表示期間5通り、グラフのタップ、追加・削除、主な暴落に戻す、今回に近い下落を探す、#cmp= の共有URL
- 各状態で 統計タイル・表・チャートSVG・詳細枠・自動文 などのHTMLを文字単位で比較し、最後にルート要素のスクショも画素で比較する
PC幅(1200px)とスマホ幅(390px)の両方で実行。差分は tests/out/parity_*.txt に書き出す
"""
import asyncio, datetime as dt, pathlib, re, sys
from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mock  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIVE = "--live" in sys.argv
if LIVE:
    mock.serve()  # file:// だと gviz が CORS で断るので http で配る
OUT = ROOT / "tests" / "out"
SHEET = "1JP-4PJimOphXB9pTvG8xCW4F12Jn5FrnHVUiT4iRVFM"
PAGE = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{max-width:860px;margin:24px auto;padding:0 16px;font-family:system-ui,sans-serif;color:#14161a}}</style></head><body>
{body}
</body></html>"""

TOOLS = {
    "list": {
        "legacy": ("legacy/list-widget.html", "#ch-root"),
        "new": ('<div data-tool="crash" data-tab="list" data-sheet="%s"></div>' % SHEET, "[data-tool] .ch-root"),
        "parts": [".ch-upd", ".ch-stats", ".ch-chart", ".ch-info", "thead", "tbody"],
    },
    "compare": {
        "legacy": ("legacy/compare-widget.html", "#cmp-root"),
        "new": ('<div data-tool="crash" data-tab="compare" data-sheet="%s"></div>' % SHEET, "[data-tool] .cmp-root"),
        "parts": [".c-lead", ".c-chips", ".c-add", ".c-range", ".c-fig", ".c-read", "thead", "tbody", ".c-sim"],
    },
}

SNAP = """([root, parts]) => { const R = document.querySelector(root); const o = {};
  for (const p of parts) { const e = R.querySelector(p); o[p] = e ? e.innerHTML : null; }
  const i = R.querySelector('.ch-info'); if (i) o['.ch-info@style'] = i.getAttribute('style');
  return o; }"""


def list_steps():
    s = []
    for cls in ("all", "bear", "corr"):
        for frm in ("1871", "1928", "1970", "2000"):
            s.append((f"cls={cls} from={frm}", f"""R => {{ R.querySelector('[data-k=cls] [data-v={cls}]').click(); R.querySelector('[data-k=from] [data-v="{frm}"]').click(); }}"""))
    s.append(("from=1871", "R => { R.querySelector('[data-k=cls] [data-v=all]').click(); R.querySelector('[data-k=from] [data-v=\"1871\"]').click(); }"))
    for col in ("name", "dd", "pk", "tr", "fall", "rec", "tot", "rc", "pk"):
        s.append((f"sort {col}", f"R => R.querySelector('th[data-s={col}]').click()"))
        s.append((f"sort {col} again", f"R => R.querySelector('th[data-s={col}]').click()"))
    s.append(("search", "R => { const i = R.querySelector('input[type=search]'); i.value = 'ショック'; i.dispatchEvent(new Event('input')); }"))
    s.append(("search clear", "R => { const i = R.querySelector('input[type=search]'); i.value = ''; i.dispatchEvent(new Event('input')); }"))
    s.append(("row tap", "R => R.querySelectorAll('tbody tr')[4].click()"))
    s.append(("row tap again", "R => R.querySelectorAll('tbody tr')[4].click()"))
    s.append(("band tap", "R => R.querySelectorAll('.ch-band')[7].dispatchEvent(new MouseEvent('click', {bubbles: true}))"))
    s.append(("band tap ongoing", "R => { const b = R.querySelectorAll('.ch-band'); b[b.length - 1].dispatchEvent(new MouseEvent('click', {bubbles: true})); }"))
    s.append(("filter keeps sel", "R => R.querySelector('[data-k=from] [data-v=\"2000\"]').click()"))
    return s


def compare_steps():
    s = [("range " + r, f"R => R.querySelector('.c-range [data-v=\"{r}\"]').click()") for r in ("90", "180", "730", "1095", "365")]
    tap = """R => { const sv = R.querySelector('.c-fig svg'), r = sv.getBoundingClientRect();
      sv.dispatchEvent(new MouseEvent('click', {bubbles: true, clientX: r.left + r.width * %s, clientY: r.top + r.height / 2})); }"""
    s.append(("tap 0.3", tap % "0.3"))
    s.append(("tap 0.85", tap % "0.85"))
    s.append(("range 90 clamps cursor", "R => R.querySelector('.c-range [data-v=\"90\"]').click()"))
    s.append(("range 365", "R => R.querySelector('.c-range [data-v=\"365\"]').click()"))
    add = """R => { const s = R.querySelector('.c-add'); s.value = s.options[%d].value; s.dispatchEvent(new Event('change')); }"""
    s.append(("add", add % 3))
    s.append(("add over max", add % 6))
    s.append(("remove chip", "R => R.querySelectorAll('.c-chips button')[1].click()"))
    s.append(("remove ongoing", "R => R.querySelectorAll('.c-chips button')[0].click()"))
    s.append(("main", "R => R.querySelector('.c-main').click()"))
    s.append(("similar", "R => R.querySelector('.c-sim').click()"))
    s.append(("range 730 after similar", "R => R.querySelector('.c-range [data-v=\"730\"]').click()"))
    s.append(("add after ALL", add % 9))
    return s


async def open_tool(b, tool, kind, width, hash_=""):
    src, root = TOOLS[tool][kind]
    if kind == "legacy":
        body = (ROOT / src).read_text(encoding="utf-8")
    else:
        body = src + '\n<script src="%s"></script>' % mock.url_for(ROOT / "dist" / "crash-tools.min.js")
        # 全画面ボタン（legacy にない追加機能）の行は隠して比べる。全画面の動きは tests/fullscreen.py で確認
        body += '\n<style>.ct-fsbar{display:none!important}</style>'
    f = OUT / f"parity_{tool}_{kind}.html"
    f.write_text(PAGE.format(body=body), encoding="utf-8")
    pg = await b.new_page(viewport={"width": width, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    if not LIVE:
        await mock.install(pg)
    await pg.goto(mock.url_for(f) + hash_)
    await pg.wait_for_function("r => { const R = document.querySelector(r); return R && R.querySelector('tbody tr'); }", arg=root)
    await pg.wait_for_timeout(300)
    return pg, root, errs


def known_diff(part, a, c):
    """legacy の既知バグによる差なら True。
    legacy の一覧は月次終値を `if(d&&v>0)` で読むため、1970-01-01（Date.UTC が 0）の点がチャートから抜ける。
    統合版はその点を描く。差が「折れ線の点が1つ多いだけ」で、その点の x が1970年1月1日の位置ならよしとする
    （位置は年の目盛り2本から線形に逆算して ±0.2px で確認）"""
    if part != ".ch-chart" or not a or not c:
        return False
    pa, pc = re.search(r' d="([^"]+)"', a), re.search(r' d="([^"]+)"', c)
    if not pa or not pc or a.replace(pa.group(1), "") != c.replace(pc.group(1), ""):
        return False
    ta, tc = re.findall(r"[\d.]+ [\d.]+", pa.group(1)), re.findall(r"[\d.]+ [\d.]+", pc.group(1))
    if len(tc) != len(ta) + 1:
        return False
    i = next((i for i in range(len(ta)) if ta[i] != tc[i]), len(ta))
    if tc[:i] + tc[i + 1:] != ta:
        return False
    ticks = [(float(x), int(y)) for x, y in re.findall(r'<text x="([\d.]+)" y="[\d.]+" font-size="10" text-anchor="middle" fill="#888">(\d{4})</text>', c)]
    if len(ticks) < 2:
        return False
    (xa, ya), (xb, yb) = ticks[0], ticks[-1]
    ms = lambda y: (dt.datetime(y, 1, 1) - dt.datetime(1970, 1, 1)).total_seconds()
    x1970 = xa + (0 - ms(ya)) / (ms(yb) - ms(ya)) * (xb - xa)
    return abs(float(tc[i].split()[0]) - x1970) < 0.2


async def snap(pg, root, parts):
    return await pg.evaluate(SNAP, [root, parts])


async def run_tool(b, tool, width, steps, hash_=""):
    parts = TOOLS[tool]["parts"]
    L, lr, le = await open_tool(b, tool, "legacy", width, hash_)
    N, nr, ne = await open_tool(b, tool, "new", width, hash_)
    diffs, n, known = [], 0, set()
    for name, js in [("initial", None)] + steps:
        if js:
            for pg, r in ((L, lr), (N, nr)):
                await pg.evaluate(f"r => ({js})(document.querySelector(r))", r)
                await pg.wait_for_timeout(250 if name.startswith("similar") else 60)
                if LIVE:  # 本物のシートは追加の取得に0.5〜1秒かかる。取得が終わる前に撮ると左右で揺れる
                    await pg.wait_for_timeout(1500)
            if name.startswith("similar"):
                for pg in (L, N):
                    await pg.wait_for_function("() => !/計算中/.test(document.querySelector('.c-sim').textContent)")
                    await pg.wait_for_timeout(200)
        a, c = await snap(L, lr, parts), await snap(N, nr, parts)
        n += 1
        for k in a:
            if a[k] != c[k]:
                if known_diff(k, a[k], c[k]):
                    known.add(name)
                else:
                    diffs.append((name, k, a[k], c[k]))
    # 見た目: ルート要素のスクショを画素で比べる（最後の状態）
    for _ in range(3):  # 描画直後はまれに撮るタイミングで揺れるので、一致しなければ少し待って撮り直す
        la = await L.locator(lr).screenshot(); na = await N.locator(nr).screenshot()
        if la == na:
            break
        await L.wait_for_timeout(500)
    (OUT / f"parity_{tool}_{width}_legacy.png").write_bytes(la); (OUT / f"parity_{tool}_{width}_new.png").write_bytes(na)
    same_px = la == na
    if not same_px:
        diffs.append(("final", "screenshot", f"{len(la)} bytes", f"{len(na)} bytes"))
    if hash_:
        hl, hn = await L.evaluate("location.hash"), await N.evaluate("location.hash")
        if hl != hn:
            diffs.append(("hash", "location.hash", hl, hn))
    for pg in (L, N):
        await pg.close()
    errs = le + ne
    return n, diffs, errs, known


async def main():
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("parity_*.txt"):
        f.unlink()
    ok = True
    async with async_playwright() as p:
        b = await mock.launch(p)
        for width in (1200, 390):
            for tool, steps, hash_ in (("list", list_steps(), ""), ("compare", compare_steps(), ""), ("compare", [], "#cmp=C010,C005,C017")):
                n, diffs, errs, known = await run_tool(b, tool, width, steps, hash_)
                label = f"{tool}{hash_} @{width}px"
                print(f"{label}: {n} states, {len(diffs)} diffs, errors={errs[:2]}" + (f", known(1970-01 point)={len(known)}" if known else ""))
                if diffs or errs:
                    ok = False
                    rep = OUT / f"parity_{tool}_{width}{'_hash' if hash_ else ''}.txt"
                    rep.write_text("\n\n".join(f"## {s} / {k}\nlegacy: {a}\nnew:    {c}" for s, k, a, c in diffs), encoding="utf-8")
                    for s, k, a, c in diffs[:3]:
                        print(f"  - {s} / {k}")
        await b.close()
    print("PARITY OK" if ok else "PARITY NG")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
