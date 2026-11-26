#!/usr/bin/env python3
"""暴落の歴史シートの週次更新案を作る（書き込みはしない）。
出力はJSON。書き込みはGoogle Sheetsコネクタで行う。
- 日次終値: シートの最終日より後の終値を追記
- 月次終値: 当月（と前月）の行を最新の月末終値で更新、なければ追記
- 暴落一覧: 継続中（回復日が空）の暴落の底を更新、高値を取り戻したら回復日を記入
            継続中がなく、最高値から10%以上下げていたら新しい暴落の行を追加
"""
import csv, io, json, sys, urllib.request, urllib.parse, datetime as dt

SID = "1JP-4PJimOphXB9pTvG8xCW4F12Jn5FrnHVUiT4iRVFM"
GID_EV, GID_M, GID_D = 257873827, 886500007, 2091119745

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")

def sheet(gid, tq=None):
    u = f"https://docs.google.com/spreadsheets/d/{SID}/gviz/tq?tqx=out:csv&gid={gid}"
    if tq:
        u += "&tq=" + urllib.parse.quote(tq)
    return list(csv.reader(io.StringIO(get(u))))

def d(s):
    return dt.date.fromisoformat(s.strip()[:10])

# シートの状態
ev = sheet(GID_EV)
H = ev[0]
col = {n: H.index(n) for n in ["ID", "名称", "ピーク日", "ピーク値", "底日", "底値", "回復日", "データ"]}
events = [r for r in ev[1:] if r[col["ID"]]]
daily_tail = sheet(GID_D, "select A,B order by A desc limit 400")[1:]
last_daily = d(daily_tail[0][0])
n_daily = int(float(sheet(GID_D, "select count(A)")[1][0]))
mon = sheet(GID_M)[1:]
all_max = sheet(GID_D, "select max(B)")[1][0]

# Yahoo（直近90日）
now = int(dt.datetime.now(dt.timezone.utc).timestamp())
y = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1={now-90*86400}&period2={now}&interval=1d"))["chart"]["result"][0]
yq = [(dt.datetime.fromtimestamp(t, dt.timezone.utc).date(), round(c, 2))
      for t, c in zip(y["timestamp"], y["indicators"]["quote"][0]["close"]) if c]
today_utc = dt.datetime.now(dt.timezone.utc).date()
# 当日分は取引中の可能性があるので、米国時間で確定した日だけ使う（UTCの今日より前）
yq = [x for x in yq if x[0] < today_utc]
new_daily = [[x[0].isoformat(), x[1]] for x in yq if x[0] > last_daily]

# 全系列（シート直近400日＋新規）
series = sorted({d(r[0]): float(r[1]) for r in daily_tail}.items()) + [(d(a), b) for a, b in new_daily]
latest_date, latest = series[-1]
ath = max(float(all_max), max(b for _, b in series))

out = {"daily_append": new_daily, "daily_next_row": n_daily + 2,
       "monthly": [], "event_updates": [], "new_event": None, "notes": []}

# 月次: 新規日の属する月ごとに月末（最新）終値
by_month = {}
for a, b in new_daily:
    by_month[a[:7]] = [a[:7] + "-01", b]
mrows = {r[0][:7]: i + 2 for i, r in enumerate(mon)}  # シートの行番号
next_m = len(mon) + 2
for k in sorted(by_month):
    if k in mrows:
        out["monthly"].append({"row": mrows[k], "values": by_month[k]})
    else:
        out["monthly"].append({"row": next_m, "values": by_month[k]}); next_m += 1

# 暴落一覧
ongo = [(i, r) for i, r in enumerate(events) if not r[col["回復日"]].strip() and "月次" not in r[col["データ"]]]
colL = "ABCDEFGHIJKLMNOPQ"
if ongo:
    i, r = ongo[-1]
    row = i + 2
    pv, tv, td = float(r[col["ピーク値"]]), float(r[col["底値"]]), d(r[col["底日"]])
    after = [(a, b) for a, b in series if a > td]
    low = min(after, key=lambda x: x[1]) if after else None
    if low and low[1] < tv:
        out["event_updates"].append({"row": row, "col": colL[col["底日"]], "value": low[0].isoformat()})
        out["event_updates"].append({"row": row, "col": colL[col["底値"]], "value": low[1]})
        out["notes"].append(f"{r[col['名称']]}: 底を更新 {low[0]} {low[1]}（ピーク比 {(low[1]/pv-1)*100:.1f}%）")
        td = low[0]
    rec = next(((a, b) for a, b in series if a > td and b >= pv), None)
    if rec:
        out["event_updates"].append({"row": row, "col": colL[col["回復日"]], "value": rec[0].isoformat()})
        out["notes"].append(f"{r[col['名称']]}: 高値を回復 {rec[0]}")
else:
    # 継続中がない: 最高値からの下落率を確認
    pk = max(series, key=lambda x: x[1])
    if pk[1] >= ath - 1e-6:
        low = min([(a, b) for a, b in series if a > pk[0]] or [pk], key=lambda x: x[1])
        if low[1] / pk[1] - 1 <= -0.10:
            nid = "C%03d" % (max(int(r[col["ID"]][1:]) for r in events) + 1)
            out["new_event"] = {"row": len(events) + 2,
                                "values": [nid, f"{low[0].year}年 （名称未定）", pk[0].isoformat(), pk[1],
                                           low[0].isoformat(), low[1], "", "", "日次終値"]}
            out["notes"].append(f"新しい下落 {nid}: {pk[0]} {pk[1]} → {low[0]} {low[1]}（{(low[1]/pk[1]-1)*100:.1f}%）。名称をユーザーに確認")
dd_now = latest / ath - 1
out["status"] = f"最新 {latest_date} 終値 {latest}、最高値 {ath} から {dd_now*100:.1f}%"
print(json.dumps(out, ensure_ascii=False, indent=1))
