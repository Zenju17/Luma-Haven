# Contributing

Read [AGENTS.md](AGENTS.md) first (stack, commands, invariants, definition of done), then [docs/HANDOVER.md](docs/HANDOVER.md) for current state.

## Workflow

1. Branch from `main` (or the agreed integration branch): `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
2. Keep changes small and focused; one concern per pull request.
3. Commit messages: `type(scope): summary` (`feat`, `fix`, `docs`, `chore`, `test`, `refactor`), with a body explaining *why* when it is not obvious.
4. Open a pull request using the checklist below. At least one reviewer other than the author.
5. Do not force-push shared branches. Do not merge or rebase `main` and long-lived branches without the owner's agreement.

## Before you open a PR

- [ ] Backend: validation, authorization, failure handling; money in integer minor units; state changes in `core/services.py` inside transactions.
- [ ] A migration for every model change; `makemigrations --check` passes.
- [ ] Tests added or updated and passing **on the disposable PostgreSQL** (`127.0.0.1:55432`), never the Supabase demo database ([docs/TESTING.md](docs/TESTING.md)).
- [ ] `manage.py check`, `npm run typecheck`, `npm run typecheck:e2e`, `npm run build` pass; user-visible flows have an E2E journey.
- [ ] No secrets, `.env*`, `backend/.private-staff-passwords`, database URIs, real guest data or card data in the diff. Seed data stays synthetic.
- [ ] Docs updated: `docs/IMPLEMENTATION_STATUS.md`, `docs/DECISIONS.md` for material choices, `docs/HANDOVER.md` if the resume point changed, `docs/PERMISSIONS.md` for role changes.
- [ ] Light/dark and mobile checked for UI changes.

## Style

- Python: follow the existing `core` monolith structure; reusable rules in `services.py`/domain modules, views only validate, authorize and call.
- Vue: Composition API with `<script setup lang="ts">`; typed API helpers in `services/api.ts`; preserve URLs and role gating.
- Write user-facing text in plain language; legal and guest-facing copy needs English and Khmer.

## Security and privacy

Report vulnerabilities as described in [docs/SECURITY.md](docs/SECURITY.md), not in public issues. Treat all guest data as confidential.

## License

The project is proprietary; see [LICENSE](LICENSE). By contributing you agree your contribution is owned by the copyright holder.
