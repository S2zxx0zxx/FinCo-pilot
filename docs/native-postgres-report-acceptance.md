# Native PostgreSQL financial report acceptance

The regular backend suite keeps its fast SQLite fixtures. Seven reporting
scenarios need PostgreSQL's `to_char()` and previously never executed. The
PostgreSQL Migration Smoke job now runs those exact scenarios sequentially
against its disposable, Alembic-migrated `finco_ci` service database.

The test harness requires all of: explicit `FINCO_TEST_DATABASE_URL`, matching
`DATABASE_URL`, development environment, `FINCO_DISPOSABLE_DB_TEST=yes`, asyncpg,
loopback host, database and role `finco_ci`, and no URL query overrides. It checks
the server's actual database/role and current runtime schema before fixture
writes. It never creates, drops or stamps a PostgreSQL schema to hide migration
failures; native pgvector is retained. The fixture cleanup deletes synthetic
rows, so this mode must never target a deployment or a restored customer branch.

Coverage includes income/expense API shape and arithmetic, opening-balance
exclusion, actual posted transfer-pair exclusion, category trends, numeric
dashboard monthly buckets, MCP monthly aggregation, and cash versus accrual
credit-card reporting. The formerly empty accounting-mode test now seeds
different purchase/effective months and checks April expenses of 30 in cash
mode (purchase date) versus 180 in accrual mode (effective bill date), while
requiring identical 180 totals across both reported months, against a fixed clock. The transfer regression
seeds both directions of a 25,000 transfer and requires zero income/expense.

SQLite still reports seven skips; they are exercised in the separate required
PostgreSQL job, not silently counted as SQLite passes. This is native database
regression evidence, not production/provider-backed acceptance or a legacy data
migration. Launch remains blocked by the master report's unresolved gates.
