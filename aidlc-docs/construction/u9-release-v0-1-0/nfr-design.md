# U9 — NFR Design

- **U9-N1.** O `check` gera os assets num só lugar (`dist/`). Confere a lista com `ls | sort` = `SHA256SUMS <whl> install.sh`. `twine check --strict`.
- **U9-N2.** ADR 0030: `VERIFY_DIST` aponta para o artefato baixado. O harness copia o wheel dali. `cmp` garante o `install.sh` byte a byte.
- **U9-N3.** `fail-fast: false` para ver as 4 plataformas. `publish` tem `needs: [check, verify]`.
- **U9-N4.** O `if` do `prerelease` monta `--prerelease --latest=false`. Promoção só por `gh release edit`, feita pelo Emerson.
- **U9-N5.** `permissions: contents: read` no topo. `publish` sobe para `contents: write`. `GH_TOKEN` = `github.token` só no passo `Criar a release`. `checkout` com `persist-credentials: false`.
- **U9-N6.** SHAs iguais aos já usados: checkout v7.0.1, setup-python v7.0.0, setup-node v7.1.0, upload-artifact v7.0.2. Novo: download-artifact `9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2`.
- **U9-N7.** Inputs entram no shell só via `env:`, nunca por `${{ }}` dentro de `run:` (evita injeção).
- **U9-N8.** As 4 somas vêm de `verify-install.sh` linhas 6–9. O teste compara os dois arquivos.
- **U9-N9.** `git ls-remote --exit-code`: rc 0 = existe (falha), rc 2 = não existe (segue), outro = falha.
- **U9-N10.** `TMPDIR: ${{ runner.temp }}` como no `verify-install.yml`. `timeout-minutes: 60` por plataforma.
- **U9-N11.** O ramo novo só roda com `VERIFY_DIST` não vazio. Help igual.
- **U9-N12.** Release-checks e ADRs sem link relativo; marcadores entre crases. `website / build` obrigatório na T2 e na T3.
- **U9-N13.** `tests/test_release_workflow.py` e `tests/test_release_checks.py` só leem arquivos. `_UNIT_ARGS` de `test_hermetic.py` não muda.

## Risco

- pytest e harness nunca rodaram em macOS nem em arm64. O E0 mostra. Se falhar, ET corretiva (T4) antes do E1.
