"""テスト用の合成データ（Googleシートと同じ列構成のCSV）を作る。
本物の株価ではない。ネットにつながらない環境で legacy と新版を同じデータで突き合わせるためのもの。
使い方: python tests/fixtures/make_fixtures.py  → tests/fixtures/{events,monthly,daily}.csv
乱数は固定シードなので、何度実行しても同じファイルになる。
"""
import csv, datetime as D, math, pathlib, random

OUT = pathlib.Path(__file__).parent
rnd = random.Random(20261126)
END = D.date(2026, 11, 25)

# 節目（日付, 水準）。この間を対数で線形補間し、小さな揺らぎ（AR(1)）を足す。水準は実際の指数に近い目安
DAILY_ANCHORS = [
    ("1927-12-30", 17.66), ("1929-09-16", 31.86), ("1932-06-01", 4.40), ("1937-03-06", 18.7),
    ("1942-04-28", 7.47), ("1946-05-29", 19.25), ("1949-06-13", 13.55), ("1956-08-02", 49.7),
    ("1957-10-22", 38.98), ("1961-12-12", 72.6), ("1962-06-26", 52.3), ("1966-02-09", 94.0),
    ("1966-10-07", 73.2), ("1968-11-29", 108.4), ("1970-05-26", 69.3), ("1973-01-11", 120.2),
    ("1974-10-03", 62.3), ("1980-11-28", 140.5), ("1982-08-12", 102.4), ("1987-08-25", 336.8),
    ("1987-12-04", 223.9), ("1990-07-16", 368.9), ("1990-10-11", 295.5), ("2000-03-24", 1527.0),
    ("2002-10-09", 776.8), ("2007-10-09", 1565.0), ("2009-03-09", 676.5), ("2011-04-29", 1363.0),
    ("2011-10-03", 1099.0), ("2015-05-21", 2131.0), ("2016-02-11", 1829.0), ("2018-09-20", 2930.0),
    ("2018-12-24", 2351.0), ("2020-02-19", 3386.0), ("2020-03-23", 2237.0), ("2022-01-03", 4796.0),
    ("2022-10-12", 3577.0), ("2025-02-19", 6144.0), ("2025-04-08", 4982.0), ("2026-08-03", 6900.0),
    ("2026-10-20", 5600.0), ("2026-11-25", 5850.0),
]
MONTHLY_ANCHORS = [
    ("1871-01-01", 4.44), ("1881-06-01", 6.58), ("1884-06-01", 4.6), ("1892-01-01", 5.6),
    ("1896-08-01", 3.9), ("1906-09-01", 10.0), ("1907-11-01", 6.3), ("1909-12-01", 10.3),
    ("1917-12-01", 6.8), ("1919-07-01", 9.5), ("1921-08-01", 6.5), ("1927-12-01", 17.5),
]
NAMES = {
    "1929-09-16": "1929〜32年 世界恐慌（大恐慌）", "1937-03-06": "1937〜42年 景気後退と戦争",
    "1956-08-02": "1956〜57年 スエズ動乱", "1961-12-12": "1962年 ケネディ・スライド",
    "1968-11-29": "1968〜70年 ニフティ・フィフティ前夜", "1973-01-11": "1973〜74年 オイルショック",
    "1980-11-28": "1980〜82年 ボルカー引き締め", "1987-08-25": "1987年 ブラックマンデー",
    "2000-03-24": "2000〜02年 ITバブル崩壊", "2007-10-09": "2007〜09年 世界金融危機（リーマン・ショック）",
    "2011-04-29": "2011年 欧州債務危機", "2018-09-20": "2018年 利上げと米中摩擦",
    "2020-02-19": "2020年 コロナ・ショック", "2022-01-03": "2022年 弱気相場（インフレ・利上げ）",
    "2025-02-19": "2025年 関税ショック", "1907-11-01": "1907年 恐慌",
}


def interp(anchors, days, sd, phi=0.97):
    pts = [(D.date.fromisoformat(d), math.log(v)) for d, v in anchors]
    out, j, e = [], 0, 0.0
    for d in days:
        while j < len(pts) - 2 and d > pts[j + 1][0]:
            j += 1
        (a, la), (b, lb) = pts[j], pts[j + 1]
        f = min(1, max(0, (d - a).days / max(1, (b - a).days)))
        e = phi * e + rnd.gauss(0, sd)
        out.append((d, round(math.exp(la + (lb - la) * f + e), 2)))
    return out


def bdays(a, b):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += D.timedelta(days=1)


def daily_series():
    return interp(DAILY_ANCHORS, list(bdays(D.date(1927, 12, 30), END)), 0.004)


def monthly_series(daily):
    # 1871〜1927: 合成の月次平均。1928〜: 日次の月末終値（1日付け）
    ms, m = [], D.date(1871, 1, 1)
    while m < D.date(1928, 1, 1):
        ms.append(m)
        m = D.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    out = interp(MONTHLY_ANCHORS, ms, 0.02, 0.6)
    last = {}
    for d, x in daily:
        if d >= D.date(1928, 1, 1):
            last[(d.year, d.month)] = x
    for (y, mo), x in sorted(last.items()):
        out.append((D.date(y, mo, 1), x))
    return out


def find_events(pts, thr=0.10):
    """高値から thr 以上下げ、高値を取り戻すまでを1件とする（テスト用の簡易版）"""
    ev, pk_i, i = [], 0, 1
    while i < len(pts):
        if pts[i][1] >= pts[pk_i][1]:
            pk_i = i
            i += 1
            continue
        if pts[i][1] / pts[pk_i][1] - 1 <= -thr:
            j, tr_i = i, i
            while j < len(pts) and pts[j][1] < pts[pk_i][1]:
                if pts[j][1] < pts[tr_i][1]:
                    tr_i = j
                j += 1
            rc = pts[j][0] if j < len(pts) else None
            ev.append((pts[pk_i], pts[tr_i], rc))
            pk_i = j if j < len(pts) else pk_i
            i = j + 1
            continue
        i += 1
    return ev


def name_for(pk, used):
    for d, n in NAMES.items():
        if abs((pk - D.date.fromisoformat(d)).days) < 90 and n not in used:
            used.add(n)
            return n
    return f"{pk.year}年 調整"


def main():
    daily = daily_series()
    monthly = monthly_series(daily)
    pre = [p for p in monthly if p[0] < D.date(1928, 1, 1)]
    evs = [(e, "月次平均") for e in find_events(pre)] + [(e, "日次") for e in find_events(daily)]
    head = ["ID", "名称", "ピーク日", "ピーク値", "底日", "底値", "回復日", "グループ", "データ",
            "Morningstar順位（実質）", "Morningstar痛み指数", "メモ", "下落率", "区分", "下落日数", "回復日数", "全期間日数"]
    rows, used = [], set()
    for n, ((pk, tr, rc), kind) in enumerate(evs, 1):
        dd = tr[1] / pk[1] - 1
        nm = "（名称未定）" if rc is None else name_for(pk[0], used)
        grp = "世界恐慌" if "世界恐慌" in nm else ""
        rows.append([f"C{n:03d}", nm, pk[0].isoformat(), f"{pk[1]:,.2f}", tr[0].isoformat(), f"{tr[1]:,.2f}",
                     rc.isoformat() if rc else "", grp, kind, "", "", "", f"{dd*100:.1f}%",
                     "弱気相場" if dd <= -0.2 else "調整", (tr[0] - pk[0]).days,
                     (rc - tr[0]).days if rc else "", (rc - pk[0]).days if rc else ""])
    # 重なりのある行（本物のシートの分割行に似せる）: 親の下落期間の途中の戻り高値→その後の安値。回復日は親と同じ
    by_date = {d: x for d, x in daily}
    for parent, nm, grp in (("C004", "1930〜32年 世界恐慌（二番底）", "世界恐慌"), ("C013", "2001年 同時多発テロ", "")):
        r = next(x for x in rows if x[0] == parent)
        a, b = D.date.fromisoformat(r[2]), D.date.fromisoformat(r[4])
        mid = [(d, x) for d, x in daily if a + (b - a) / 3 <= d <= a + (b - a) * 2 / 3]
        pk = max(mid, key=lambda t: t[1])
        tr = min([(d, x) for d, x in daily if pk[0] < d <= b + D.timedelta(days=200)], key=lambda t: t[1])
        rc = D.date.fromisoformat(r[6])
        dd = tr[1] / pk[1] - 1
        if grp:
            r[7] = grp
        rows.append([f"C{len(rows)+1:03d}", nm, pk[0].isoformat(), f"{pk[1]:,.2f}", tr[0].isoformat(), f"{tr[1]:,.2f}",
                     rc.isoformat(), grp, "日次", "", "", "", f"{dd*100:.1f}%", "弱気相場" if dd <= -0.2 else "調整",
                     (tr[0] - pk[0]).days, (rc - tr[0]).days, (rc - pk[0]).days])
    w = lambda name, h, data: csv.writer(open(OUT / name, "w", newline="", encoding="utf-8"), quoting=csv.QUOTE_ALL).writerows([h] + data)
    w("events.csv", head, rows)
    w("monthly.csv", ["月", "終値"], [[d.isoformat(), f"{x:,.2f}"] for d, x in monthly])
    w("daily.csv", ["日付", "終値"], [[d.isoformat(), f"{x:,.2f}"] for d, x in daily])
    print(f"events={len(rows)} monthly={len(monthly)} daily={len(daily)}")


if __name__ == "__main__":
    main()
