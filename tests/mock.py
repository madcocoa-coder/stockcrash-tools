"""テスト用の共通部品: ブラウザ起動と、Googleシート（gviz）へのリクエストを合成データで差し替える仕組み。
合成データは tests/fixtures/make_fixtures.py で作る（本物の株価ではない）。
"""
import csv, io, os, pathlib, re, urllib.parse

FIX = pathlib.Path(__file__).parent / "fixtures"
GIDS = {"257873827": "events.csv", "886500007": "monthly.csv", "2091119745": "daily.csv"}
FIXED_NOW = "2026-11-26T03:00:00Z"  # Date.now() を固定（一覧の右端・比較の期間の計算をそろえる）
_cache = {}


async def launch(p):
    """Playwright の Chromium。同梱のブラウザが見つからない環境では /opt/pw-browsers/chromium などを使う"""
    exe = os.environ.get("CHROMIUM_PATH")
    if exe:
        return await p.chromium.launch(executable_path=exe)
    try:
        return await p.chromium.launch()
    except Exception:
        alt = "/opt/pw-browsers/chromium"
        if os.path.exists(alt):
            return await p.chromium.launch(executable_path=alt)
        raise


def _text(name):
    if name not in _cache:
        _cache[name] = (FIX / name).read_text(encoding="utf-8")
    return _cache[name]


def gviz_body(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    name = GIDS.get((q.get("gid") or [""])[0])
    if not name:
        return None
    body = _text(name)
    tq = (q.get("tq") or [""])[0]
    if tq:  # select A,B where A >= date 'X' and A <= date 'Y' order by A だけ解釈する
        m = re.search(r"A >= date '([\d-]+)' and A <= date '([\d-]+)'", tq)
        rows = list(csv.reader(io.StringIO(body)))
        keep = [rows[0]] + [r for r in rows[1:] if m and m.group(1) <= r[0] <= m.group(2)]
        out = io.StringIO()
        csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(keep)
        body = out.getvalue()
    return body


async def install(page, log=None):
    await page.clock.set_fixed_time(FIXED_NOW)

    async def handle(route):
        url = route.request.url
        if log is not None:
            log.append(url)
        body = gviz_body(url)
        if body is None:
            await route.fulfill(status=404, body="not found")
        else:
            await route.fulfill(status=200, body=body, headers={"content-type": "text/csv; charset=utf-8", "access-control-allow-origin": "*"})

    await page.route("https://docs.google.com/**", handle)
