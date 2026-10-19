"""Scans the S&P 500 and writes signals.json. Usage: python scan.py
Deps: pip install yfinance pandas requests lxml"""
import io, json, datetime as dt
import pandas as pd, requests, yfinance as yf

BUY_AT, SELL_AT = 3, -3

def sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    t = pd.read_html(io.StringIO(html))[0]
    return [(r["Symbol"].replace(".", "-"), r["Security"], r["GICS Sector"]) for _, r in t.iterrows()]

def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)

def atr(df, n=14):
    pc = df["Close"].shift()
    tr = pd.concat([df["High"]-df["Low"], (df["High"]-pc).abs(), (df["Low"]-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def analyze(df):
    c = df["Close"]
    sma50, sma200 = c.rolling(50).mean(), c.rolling(200).mean()
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    p, r, a = c.iloc[-1], rsi(c).iloc[-1], atr(df).iloc[-1]
    score = (1 if p > sma50.iloc[-1] else -1) + (1 if sma50.iloc[-1] > sma200.iloc[-1] else -1) \
          + (1 if macd.iloc[-1] > sig.iloc[-1] else -1) + (1 if r < 30 else -1 if r > 70 else 0)
    s = "BUY" if score >= BUY_AT else "SELL" if score <= SELL_AT else "HOLD"
    sl = tp = None
    if s == "BUY": sl, tp = p - 1.5*a, p + 3*a
    if s == "SELL": sl, tp = p + 1.5*a, p - 3*a
    f = lambda x: None if x is None else round(float(x), 2)
    return dict(price=f(p), chg=f((p / c.iloc[-2] - 1) * 100), rsi=f(r), score=int(score), signal=s, stop=f(sl), target=f(tp)), df.index[-1].date()

def main():
    meta = {s: (n, sec) for s, n, sec in sp500()}
    syms, out, as_of = list(meta), [], None
    for i in range(0, len(syms), 100):
        chunk = syms[i:i+100]
        data = yf.download(chunk, period="1y", interval="1d", auto_adjust=True,
                           group_by="ticker", progress=False, threads=True)
        for s in chunk:
            try:
                df = data[s].dropna()
                if len(df) < 210: continue
                res, d = analyze(df)
                as_of = max(as_of, d) if as_of else d
                out.append(dict(symbol=s, name=meta[s][0], sector=meta[s][1], **res))
            except Exception as e:
                print(s, "skipped:", e)
    out.sort(key=lambda x: -x["score"])
    json.dump(dict(generated=dt.datetime.utcnow().isoformat() + "Z", as_of=str(as_of),
                   count=len(out), signals=out), open("signals.json", "w"))
    print(f"Wrote {len(out)} signals")

if __name__ == "__main__":
    main()
