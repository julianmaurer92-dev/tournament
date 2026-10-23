# Migrationen

CupPlan benutzt (noch) kein Alembic. Schema-Aenderungen laufen ueber
`_migrate_db()` in `app/__init__.py`: eine Liste idempotenter, rein additiver
SQL-Anweisungen, die bei jedem Start ausgefuehrt werden.

Regeln:
- nur `ADD COLUMN IF NOT EXISTS` mit Default, nie `DROP`/`RENAME`
- neue Tabellen entstehen automatisch durch `db.create_all()`
- jede Aenderung hier dokumentieren (Datum, Grund)

## Verlauf

- (Bestand) `match.field`, `match.is_penalty`, `tournament.event_time`,
  `tournament_settings.value` -> TEXT
