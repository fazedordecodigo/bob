# U9 — NFR Requirements

| Id | Origem | Requisito | Como medir |
|---|---|---|---|
| U9-N1 | NFR1 | Os 3 assets saem iguais ao CT12: nomes exatos, `SHA256SUMS` = `sha256sum install.sh <whl> \| LC_ALL=C sort -k2` | passo do `check` + `test_release_builds_the_three_assets` |
| U9-N2 | NFR3 | O `verify` usa o wheel do run, não outro | `VERIFY_DIST` + `cmp` do `install.sh` + `shasum -c` |
| U9-N3 | NFR10 | Verificação nas 4 plataformas antes de publicar | matriz + `needs: [check, verify]` |
| U9-N4 | NFR11 | Pré-release não vira latest | `--prerelease --latest=false`; E2 = `404` |
| U9-N5 | segurança | Só `publish` tem `contents: write`; topo `contents: read` | `test_release_jobs_and_permissions` |
| U9-N6 | segurança | Actions fixadas por SHA de 40 hex com comentário de versão | `test_release_pins_actions_like_ci` + testes existentes |
| U9-N7 | segurança | Sem `secrets.`, `sudo`, `pull_request`, `push:` no `release.yml` | idem |
| U9-N8 | integridade | gitleaks por plataforma conferido por sha256, iguais aos do harness | `test_release_matrix_is_the_four_platforms` |
| U9-N9 | operação | Tag diferente da versão, tag inválida ou existente param antes de gerar | passo `meta` + "Tag ainda não existe" |
| U9-N10 | tempo | Passo 2 e passo 10 do harness ≤ 300 s em cada runner | o harness já falha acima disso |
| U9-N11 | compat. | Sem `VERIFY_DIST`, o harness faz o mesmo de hoje | testes atuais do harness verdes + 2 casos novos |
| U9-N12 | docs | Site compila com as 22 ADRs e os release-checks (`onBrokenLinks: throw`) | check `website / build` |
| U9-N13 | testes | Testes novos só leem arquivos; não entram na guarda hermética | revisão do diff |
