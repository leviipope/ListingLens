# Database migrations

Migration files are located in:

`alembic/versions/`

Use sequential revision IDs:

```powershell
uv run alembic revision --autogenerate --rev-id 002 -m "describe the change"
```

After reviewing the migration:

```powershell
uv run alembic upgrade head
uv run alembic current
uv run alembic downgrade -1
uv run alembic upgrade head
```

To view migration history:

```powershell
uv run alembic history
```

Run these commands from the repository root.

Note: Docker container updates to head by itself.