# bob

Plugin de qualidade: fluxo de spec do Pocock + gates `bob check`.

## Skills

- **bob-check** (`skills/bob-check/SKILL.md`): run `bob check`, read the JSON, iterate until exit 0.
- **review-report** (`skills/review-report/SKILL.md`): fold `.bob/report.md` into the PR body; companion to `pr`.
- **Pocock** (`skills/vendor/mattpocock/`): MIT. `grill-me` → `to-spec` → `to-tickets` → `implement-spec` / `tdd` → `code-review`. Source and license: `NOTICE`.

## Check

`bob check` is the gate. Local hook: `crap,dry,deps`. CI: all gates. Exit 0 is the only pass. CLI surface: `docs/SPEC.md`.
