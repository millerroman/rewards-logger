# rewards-logger

Read-only logger of public Polymarket order books for a fixed set of 200 liquidity-reward markets (`markets.json`).
It samples the books about once a minute for three days and stores compact snapshots in `data/`.
No orders, no keys, public endpoints only. Runs in GitHub Actions until `END_AT` in the workflow file.
