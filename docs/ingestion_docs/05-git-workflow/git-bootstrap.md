# Git Bootstrap and Workflow

## Repository Init

```bash
git init
```

## Branch Strategy

- `main`: protected integration branch.
- `epic/<id>-<slug>`: epic-level implementation branch.
- `story/<id>-<slug>`: small scoped implementation branches if needed.

## Commit Convention

`<type>(<scope>): <summary>`

Types:
- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`
- `infra`

## PR/Review Checklist

1. Contract compatibility checked.
2. Tests and lint pass.
3. Observability coverage added for new services.
4. Runbook impact reviewed.
5. Migration/rollback notes attached for infra or schema changes.
