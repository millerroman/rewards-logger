"""One-off: pick the fixed set of reward markets to log. Reads public CLOB rewards listing, writes markets.json.
Selection: rate >= $10/day, Yes price 0.12-0.88, > 14 days to resolution, max spread > 0; 200 random (seed 7)."""
import json, random, datetime, urllib.request, urllib.parse
UA = {"User-Agent": "rewards-logger/1.0"}
def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
out, cur = [], None
for _ in range(60):
    q = {"order_by": "rate_per_day", "position": "DESC", "page_size": "500"}
    if cur: q["next_cursor"] = cur
    d = get("https://clob.polymarket.com/rewards/markets/multi?" + urllib.parse.urlencode(q))
    out += d["data"]; cur = d.get("next_cursor")
    if not d["data"] or cur in (None, "LTE="): break
    if sum(c["rate_per_day"] for c in d["data"][-1]["rewards_config"]) < 10: break
rate = lambda m: sum(c["rate_per_day"] for c in m["rewards_config"])
cut = (datetime.datetime.utcnow() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
c = [m for m in out if rate(m) >= 10 and 0.12 <= m["tokens"][0]["price"] <= 0.88
     and str(m["end_date"])[:10] > cut and m["rewards_max_spread"] > 0]
random.seed(7); s = random.sample(c, min(200, len(c)))
sel = [dict(cid=m["condition_id"], token=m["tokens"][0]["token_id"], q=m["question"], rate=rate(m),
            max_spread=m["rewards_max_spread"], min_size=m["rewards_min_size"], end=str(m["end_date"])[:10],
            vol24=m.get("volume_24hr"), comp=m.get("market_competitiveness")) for m in s]
json.dump(sel, open("markets.json", "w"), indent=0)
print("listed", len(out), "candidates", len(c), "selected", len(sel), "sum rate $/day", round(sum(x["rate"] for x in sel)))
