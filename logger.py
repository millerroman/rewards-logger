"""Read-only logger of Polymarket order books for a fixed set of liquidity-reward markets.
Public unauthenticated endpoints only; places no orders and uses no keys.
Every ~60 s (random offset) it fetches the books and appends one compact JSON line per market to data/books-<UTC hour>.jsonl.gz
usage: logger.py <run_minutes>"""
import json, gzip, time, random, sys, os, datetime, urllib.request
RUN_MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 5
END_AT = os.environ.get("END_AT", "")          # ISO date-time (UTC); logger refuses to run after it
UA = {"User-Agent": "rewards-logger/1.0", "Content-Type": "application/json"}
M = json.load(open("markets.json"))
now = lambda: datetime.datetime.now(datetime.timezone.utc)
if END_AT and now().strftime("%Y-%m-%dT%H:%M") >= END_AT:
    print("past END_AT, nothing to do"); sys.exit(0)

def post(url, body, timeout=30):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), headers=UA, method="POST")
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read())

def fetch_books():
    books = {}
    for i in range(0, len(M), 100):
        chunk = M[i:i + 100]
        for attempt in range(3):
            try:
                for b in post("https://clob.polymarket.com/books", [{"token_id": m["token"]} for m in chunk]):
                    books[b["asset_id"]] = b
                break
            except Exception as e:
                err = repr(e)[:200]
                if "403" in err or "451" in err:      # access refused from this location: stop, do not work around it
                    print("ACCESS REFUSED, stopping:", err); sys.exit(2)
                time.sleep(2 + 3 * attempt)
        else:
            print("chunk failed", i, err, flush=True)
    return books

def compact(m, b, ts):
    bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids", [])), reverse=True)
    asks = sorted(((float(x["price"]), float(x["size"])) for x in b.get("asks", [])))
    row = {"t": ts, "c": m["cid"][:12], "bt": b.get("timestamp")}
    if bids and asks:
        mid = (bids[0][0] + asks[0][0]) / 2; w = 2 * m["max_spread"] / 100 + 1e-9
        row.update(bb=bids[0][0], ba=asks[0][0],
                   b=[[p, round(z, 1)] for p, z in bids if mid - p <= w][:25],
                   a=[[p, round(z, 1)] for p, z in asks if p - mid <= w][:25])
    else:
        row.update(bb=bids[0][0] if bids else None, ba=asks[0][0] if asks else None, b=[], a=[])
    return row

t_end = time.time() + RUN_MIN * 60
n = 0
while time.time() < t_end:
    t0 = time.time(); ts = int(t0)
    books = fetch_books()
    fn = "data/books-" + now().strftime("%Y%m%d-%H") + ".jsonl.gz"
    with gzip.open(fn, "at") as f:
        for m in M:
            b = books.get(m["token"])
            if b: f.write(json.dumps(compact(m, b, ts), separators=(",", ":")) + "\n")
    n += 1
    if n % 10 == 1: print(now().strftime("%H:%M:%S"), "sample", n, "books", len(books), "of", len(M), "took", round(time.time() - t0, 1), "s", flush=True)
    # next sample at a random offset inside the next minute (rewards are sampled at a random second each minute)
    nxt = (int(t0) // 60 + 1) * 60 + random.uniform(0, 59)
    time.sleep(max(1.0, min(nxt - time.time(), t_end - time.time())))
print("done, samples", n)
