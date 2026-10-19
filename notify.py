"""Sends top S&P 500 signals from signals.json to Telegram.
Env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SITE_URL (optional)"""
import json, os, requests

TOP = 10
d = json.load(open("signals.json"))
sig = d["signals"]
buys = sorted([x for x in sig if x["signal"] == "BUY"], key=lambda x: (-x["score"], x["rsi"]))[:TOP]
sells = sorted([x for x in sig if x["signal"] == "SELL"], key=lambda x: (x["score"], -x["rsi"]))[:TOP]
n = lambda s: sum(1 for x in sig if x["signal"] == s)

def line(x, icon):
    return f"{icon} {x['symbol']} {x['price']:.2f} ({x['chg']:+.1f}%) RSI {x['rsi']:.0f}\n    SL {x['stop']:.2f} | TP {x['target']:.2f}"

parts = [f"📊 S&P 500 signals (US close {d['as_of']})",
         f"Buy {n('BUY')} · Sell {n('SELL')} · Hold {n('HOLD')}"]
if buys: parts += ["\nTop BUY"] + [line(x, "🟢") for x in buys]
if sells: parts += ["\nTop SELL"] + [line(x, "🔴") for x in sells]
if os.getenv("SITE_URL"): parts.append(f"\nFull list: {os.environ['SITE_URL']}")
parts.append("\n⚠️ Not financial advice.")

r = requests.post(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage",
    data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": "\n".join(parts),
          "disable_web_page_preview": "true"}, timeout=20)
r.raise_for_status()
print("Sent")
