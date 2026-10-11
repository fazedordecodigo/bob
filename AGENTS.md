# bob

Plugin de qualidade: fluxo de spec do Pocock + gates `bob check`.

## Skills

- **bob-check** (`skills/bob-check/SKILL.md`): ao verificar um diff ou quando um gate falhar.
- **review-report** (`skills/review-report/SKILL.md`): ao escrever o PR depois de `bob check`.
- **Pocock** (`skills/vendor/mattpocock/`): `grill-me` → `to-spec` → `to-tickets` → `implement-spec` / `tdd` → `code-review`. MIT: `NOTICE`.

## Check

`bob check`. Superfície e exit codes: `docs/SPEC.md`.

## Cursor Cloud specific instructions

- Python ≥ 3.10 da imagem padrão. Este branch não tem dependências de terceiros: os testes usam `unittest` da biblioteca padrão.
- Contrato das skills: `python3 -m unittest discover -s tests -v`.
- Não há servidor, banco nem processo de boot. A CLI `bob` ainda não está no repositório.
