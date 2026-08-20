# api

Generated code. Nothing in here is written by hand.

`npm run generate` reads `openapitools.json` and writes `trade/` from
`contracts/trade-api.yaml` and `auth/` from `contracts/auth-api.yaml`. Both directories are
committed, so the build works without a Java runtime and a contract change shows up as a
reviewable diff.

Never edit a file under `trade/` or `auth/`. The next regeneration overwrites it, so an edit
here is a change that survives until the next `npm run generate` and no longer. When the
generated shape is awkward to consume, wrap it in a service in `../services/`.
