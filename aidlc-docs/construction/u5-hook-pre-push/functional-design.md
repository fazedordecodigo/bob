# U5 — u5-hook-pre-push — Desenho funcional (3.1, Minimal)

Unit: U5 | Kind: library | Dona de: C06 (`src/bob_quality/hook_install.py`) | Estende: C02 (passo `hook` do `bob setup`, CT3 ordem 7), harness (CT15: passos 6 e 12 novos; passos 7 e 8 conferem o hook)
Contrato de que é dona: CT10. Consome: CT1, CT3, CT5 (`BobHome.bin_bob`, marcador do hook), CT15 (U1).
ADR: 0016 (hook gerenciado; complemento da U5 em `decisions.md`), 0017 (preservação, posse, idempotência), 0013 (launcher estável `BOB_HOME/bin/bob`).
Histórias e requisitos: US4.1 (dona); contribui para a US3.2 (hook); FR5.1, FR5.2, FR5.3; NFR4, NFR5, NFR8.
Base lida: `fazedordecodigo/bob` `main` @ `b142631935df7cad40f241501969dfea03595057` (#199, U4 fechada; leitura remota por `raw.githubusercontent.com` e pela API pública, sem clone). Data: 2026-10-22 09:1x (UTC-3).

## O que passa a existir
O `bob setup` ganha o passo `hook`, depois de `bob.yaml`. Ele grava `$(git rev-parse --git-path hooks)/pre-push` com o template do CT10: a linha 2 é `# managed-by: bob-quality` e o hook chama o launcher estável `BOB_HOME/bin/bob` pelo caminho absoluto. Assim o hook funciona num `git push` comum, sem ativar ambiente e sem `bob` no `PATH`. O bob nunca escreve num hook que não é dele (sem a marca, link ou pasta) nem num repo com `core.hooksPath`: preserva, lista em `preservado:` e avisa com a linha a acrescentar. Um hook do bob igual ao template não é regravado. O harness ganha o passo 6 (push para um remoto bare com `env -i HOME=$HOME PATH=/usr/bin:/bin`) e o passo 12 (`tests/test_hook.py`, agora com o hook gerado). Os passos 7 e 8 passam a conferir o hook.

```
bob setup: projeto → runtimes → npm → gitleaks → skills → bob.yaml → hook → [doctor] → resumo
  hook: render_hook(BOB_BIN) (caminho absoluto e citável? senão falha 4, nada gravado)
        git config --get core.hooksPath → saída 0? → preserved_hookspath (nada gravado, aviso)
        git rev-parse --git-path hooks → <hooks>/pre-push
          link ou não-arquivo            → preserved (0 leituras, 0 escritas, aviso)
          arquivo sem a linha 2 exata    → preserved (0 escritas, aviso)
          arquivo do bob, igual e 0755   → unchanged (0 escritas)
          arquivo do bob, diferente      → pre-push.tmp-<pid> → chmod 0755 → os.replace → updated
          não existe                     → mkdir <hooks> (exist_ok) → idem → created
```

## Estado atual do repo (conferido @ b142631)
| Ponto | Hoje | Onde |
|---|---|---|
| Instalador do hook | não existe (`src/bob_quality/hook_install.py` ausente na árvore) | árvore da `main` (374 arquivos) |
| Hook estático | 5 linhas: `#!/bin/sh`, `set -e`, `unset PYTEST_ADDOPTS`, `unset PYTEST_PLUGINS`, `exec bob check --gates crap,dry,deps </dev/null`; empacotado por `hooks/*` | `src/bob_quality/hooks/pre-push:1-5`; `pyproject.toml` `[tool.setuptools.package-data]` |
| Docs do hook | `cp src/bob_quality/hooks/pre-push .git/hooks/pre-push` manual (dono: U8) | `README.md:319-326`, `docs/guides/pre-push.md` |
| `bob setup` | `STEPS = (projeto, runtimes, npm, gitleaks, skills, bob.yaml)`; o doctor roda fora de `STEPS`, em `_run` | `setup_cmd.py:215-222`, `_run` `:267-284` |
| Modelo de passo | `step_bob_yaml` (`:201-212`), `_failed_reason` (`:348-349`), `_skills_write_error` (`:390-395`), `_relative` (`:433-434`); constantes de chave `:52-112` | `setup_cmd.py` |
| Saída de aviso | `_announce` imprime `bob setup: {step}: warning: {text}` (pt: `aviso:`); o resumo imprime `  preserved: {item}` e `  warnings: {text}` | `setup_cmd.py` `_announce`, `_summary`; `messages.py:398`, `:403-404`, `:809`, `:814-815` |
| Launcher | `BobHome.bin_bob = root / "bin" / "bob"`, `root` absoluto (`BOB_HOME` relativo → `ValueError`) | `user_dirs.py:12-43` (`BobHome` na 13, `bob_home` na 22) |
| Mensagens | `_EN` termina em `setup.bob_yaml_write` (`:453-455`, `}` na 456); `_PT_BR` em `:867-869` (`}` na 870); `git.ls_files_failed` en `:92`, pt `:500`; `tool.missing` en `:90`, pt `:498` | `messages.py` |
| Teste do hook | copia o estático com `shutil.copy` (`_install_hook`, `:27-32`) e roda o arquivo; 6 testes; 2 medem `< 60` s | `tests/test_hook.py:16`, `:27-32`, `:35-164` |
| `bob check` | não imprime relatório no stdout; grava `.bob/report.md` (`# bob report`, linhas ``- <marca> `<gate>`: <status>``) e `.bob/report.json` | `cli.py`, `messages.py:229-234` |
| Harness | `STEP_IDS='1 2 3 4 5 7 8 9a 9b'` (`:4`); `ensure_2` (`:772-777`); `step_7` (`:919-987`, `digest` inclui `.git/hooks`); `step_8` (`:989-1063`); `run_selected` (`:1165-1191`, `3\|4\|5\|7) ensure_2` na `:1177`) | `scripts/verify-install.sh` |
| Testes do harness | `_HELP` (`:19-23`), `test_step_ids_are_the_u1_u3_and_u4_steps` (`:88-89`), `test_step_5_is_wired` (`:139-145`), `test_usage_errors_exit_1_before_preparing` usa `--only 6` como passo desconhecido (`:225-266`) | `tests/test_verify_install.py` |
| pytest no harness | o workflow `verify-install` não instala `.[dev]`; `pytest==9.1.1` só no extra `dev` | `.github/workflows/verify-install.yml`; `pyproject.toml` |

## Regras de negócio
| # | Regra | Origem |
|---|---|---|
| H1 | `render_hook(bob_bin)` devolve os bytes do template CT10 (8 linhas, LF, termina em `\n`), com `os.fsencode(bob_bin)` no lugar de `<BOB_BIN>`. Sem literal de codificação no código. | CT10, ADR 0016 |
| H2 | `bob_bin` não absoluto, ou com algum dos bytes `"`, `$`, `` ` ``, `\` ou `\n` → `HookPathError` (subclasse de `ValueError`). Nada roda nem é gravado. A checagem usa uma tupla de 5 literais de 1 byte cada. | CT10 ("absoluto, sem aspas internas"), I38 |
| H3 | `git config --get core.hooksPath` no projeto: saída `0` → `HookResult("preserved_hookspath", path, hooks_path=<valor>)`, com `<valor>` = stdout até o 1º `\n` (`partition`), `path` = `project / <valor>`. Nada é gravado nem criado. Saída `1` → segue. Outra saída → `ToolError(git.command_failed)`. | ADR 0016, CT10, FR5.3 |
| H4 | `git rev-parse --git-path hooks` no projeto (saída ≠ `0` → `ToolError(git.command_failed)`); `dest = project / <stdout até o 1º \n> / "pre-push"` (caminho absoluto em worktree também funciona). | ADR 0016, CT10 |
| H5 | `dest` é link (mesmo quebrado ou para um hook do bob) ou existe e não é arquivo regular → `preserved`, sem ler e sem escrever. | ADR 0017, I38 |
| H6 | `dest` é arquivo regular: lê os bytes. Do bob só se `bytes.split(b"\n")[1:2] == [HOOK_MARKER]` (linha 2 exata; CRLF, espaço no fim ou marca em outra linha → alheio). Alheio → `preserved`, 0 escritas. | CT5 (linha 2 exata), CT10, FR5.3 |
| H7 | Do bob, bytes iguais a `render_hook` e modo `0o755` → `unchanged`, 0 escritas. Senão → grava (H9) → `updated`. | CT10, ADR 0017, NFR4 |
| H8 | `dest` não existe → `dest.parent.mkdir(exist_ok=True)` (sem `parents`) → grava (H9) → `created`. | CT10 |
| H9 | Gravação: `tmp = dest.with_name(f"pre-push.tmp-{os.getpid()}")`; `tmp.write_bytes(texto)`; `os.chmod(tmp, _MODE)` com `_MODE = 0o755`; `os.replace(tmp, dest)`. Qualquer exceção nesses três passos: `tmp.unlink(missing_ok=True)` e a exceção sobe sem mudança. | ADR 0017, CT10 (modo `0755`) |
| H10 | `OSError` ao rodar o git → `ToolError(msg("tool.missing", tool="git"))`. Os dois comandos rodam com `cwd=project`, `capture_output=True`, `text=True`, `check=False`. | CT1, padrão de `suite_fingerprint._listed_files` |
| H11 | Passo `hook` (tabela abaixo). Não imprime nada; o `bob setup` imprime a linha do passo, os avisos e o resumo (CT3). | CT3 |
| H12 | Nenhuma pergunta ao dev; a 2ª execução não grava nada (H7). | NFR4, R-S3 |
| H13 | O hook estático `src/bob_quality/hooks/pre-push` não muda (caminho manual dos docs, que são da U8). Um teste prende o comando dele ao do template. | CT10 ("preservado do repo"), I40 |

## Interface de `hook_install.py` (CT10 + acréscimos compatíveis)
```python
HOOK_MARKER = b"# managed-by: bob-quality"
HookState = Literal["created", "updated", "unchanged", "preserved", "preserved_hookspath"]

class HookPathError(ValueError): ...           # acréscimo (H2)

@dataclass(frozen=True)
class HookResult:
    state: HookState
    path: Path
    hooks_path: str = ""                        # acréscimo: valor cru de core.hooksPath (H3)

def render_hook(bob_bin: Path) -> bytes: ...    # acréscimo (H1, H2)
def install_hook(project: Path, bob_bin: Path) -> HookResult: ...   # CT10; HookPathError, ToolError e OSError sobem
```
Template (bytes; `<BOB_BIN>` = `os.fsencode(bob_bin)`), linha a linha: `#!/bin/sh` · `# managed-by: bob-quality` · `set -e` · `unset PYTEST_ADDOPTS` · `unset PYTEST_PLUGINS` · `BOB="<BOB_BIN>"` · `[ -x "$BOB" ] || BOB=bob` · `exec "$BOB" check --gates crap,dry,deps </dev/null`. A linha 2 vem de `HOOK_MARKER` (um literal só).

## Passo `hook` no `bob setup` (CT3, ordem 7)
`P` = caminho mostrado: `result.path` relativo a `ctx.project` (POSIX) se estiver dentro dele; senão `str(result.path)`. `B` = `str(ctx.home.bin_bob)`.

| Situação | `StepResult` |
|---|---|
| `created` | `installed`, `installed=(msg("setup.item_hook", path=P),)` |
| `updated` | `installed`, `installed=(msg("setup.item_hook_updated", path=P),)` |
| `unchanged` | `unchanged` (nenhum item) |
| `preserved` | `preserved`, `preserved=(msg("setup.preserved_hook", path=P),)`, `warnings=(msg("setup.warn_hook_foreign", path=P, bob=B),)` |
| `preserved_hookspath` | `preserved`, `preserved=(msg("setup.preserved_hookspath", value=V),)`, `warnings=(msg("setup.warn_hookspath", value=V, bob=B),)`, `V = result.hooks_path` |
| `HookPathError` | `failed`, `error=msg("setup.hook_bad_path", path=B)` |
| `ToolError` | `failed`, `error=_failed_reason("hook", exc)` (texto `hook: <motivo>`) |
| `OSError` | `failed`, `error=msg("setup.hook_write", path=exc.filename or ".git/hooks/pre-push", detail=exc.strerror or type(exc).__name__)` |
`STEPS` = `projeto`, `runtimes`, `npm`, `gitleaks`, `skills`, `bob.yaml`, `hook`.

## Mensagens (catálogo `messages.py`, en e pt-BR)
| Chave | en | pt-BR |
|---|---|---|
| `git.command_failed` (T1) | `git {command} failed: {detail}` | `git {command} falhou: {detail}` |
| `setup.item_hook` | `pre-push hook ({path})` | `hook pre-push ({path})` |
| `setup.item_hook_updated` | `pre-push hook ({path}; updated)` | `hook pre-push ({path}; atualizado)` |
| `setup.preserved_hook` | `{path} (pre-push hook without the bob marker)` | `{path} (hook pre-push sem a marca do bob)` |
| `setup.preserved_hookspath` | `core.hooksPath={value} (bob does not write there)` | `core.hooksPath={value} (o bob não grava lá)` |
| `setup.warn_hook_foreign` | `existing pre-push hook preserved ({path}). To use bob's, add: {bob} check --gates crap,dry,deps.` | `hook pre-push existente preservado ({path}). Para usar o do bob, acrescente: {bob} check --gates crap,dry,deps.` |
| `setup.warn_hookspath` | `core.hooksPath={value}; hook not installed. Add to your hook manager: {bob} check --gates crap,dry,deps.` | `core.hooksPath={value}; hook não instalado. Acrescente ao seu gerenciador de hooks: {bob} check --gates crap,dry,deps.` |
| `setup.hook_bad_path` | ``hook: the hook cannot call {path} (the path must be absolute, without ", $, \, ` or a line break). Set BOB_HOME to another folder and run the install again.`` | ``hook: o hook não consegue chamar {path} (o caminho precisa ser absoluto, sem ", $, \, ` nem quebra de linha). Defina BOB_HOME em outra pasta e rode a instalação de novo.`` |
| `setup.hook_write` | `hook: could not write {path} ({detail}). Check the permissions.` | `hook: não consegui gravar {path} ({detail}). Confira as permissões.` |

Os textos pt de `setup.warn_hook_foreign` e `setup.warn_hookspath` são os do CT10, sem o prefixo `hook: aviso:`, que vem de `setup.warning_line` (I36). Na saída (en): `bob setup: hook: ok`; `bob setup: hook: warning: existing pre-push hook preserved (.git/hooks/pre-push). To use bob's, add: /home/u/.local/share/bob-quality/bin/bob check --gates crap,dry,deps.`; no resumo, `  installed: …, pre-push hook (.git/hooks/pre-push)`, `  preserved: .git/hooks/pre-push (pre-push hook without the bob marker)`, `  warnings: existing pre-push hook preserved (…)`.

## Harness (CT15; passos 6, 7, 8 e 12)
| Passo | Muda |
|---|---|
| ids | `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 12'`; comentário da linha 2 com `1, 2, 3, 4, 5, 6, 7, 8, 9a, 9b e 12`; `run_selected` faz `3\|4\|5\|6\|7\|12) ensure_2`. |
| 6 (novo) | Depende do passo 2 (usa `S2_HOME`). Projeto novo `$T/s6/proj` (`src/app.py`, 1 commit) e remoto bare `$T/s6/remote.git`; `git remote add origin` e `git push -q origin HEAD:main` antes da instalação (sem hook ainda). Comando único com `S2_HOME` → sai `0`, última linha `  bob doctor: 0`. O hook gravado é byte a byte `expected_hook "$S2_HOME/.local/share/bob-quality/bin/bob"`, modo `755`. Commit novo (`src/feature.py`, mais o que o setup criou). `git push origin HEAD:main` com `env -i "HOME=$S2_HOME" PATH=/usr/bin:/bin` → sai `0`; o remoto tem o commit; `.bob/report.md` existe, começa com `# bob report` e tem as linhas de `crap`, `dry` e `deps`. Imprime `verify-install: passo 6: tempo <s> s` (só o push). |
| 7 | Além do `digest` (que já cobre `.git/hooks`): o hook do `S2_PROJ` existe antes da 2ª execução e o `st_mtime_ns` dele não muda (`o hook foi regravado`). |
| 8 | O projeto ganha um hook do dev em `.git/hooks/pre-push` (`#!/bin/sh`, `# hook do dev`, `exit 0`; modo 0755), fora do git. Ele entra na conferência por sha, e o stdout tem `  preserved: .git/hooks/pre-push (pre-push hook without the bob marker)` e a linha de aviso com o launcher de `$T/s8/home`. |
| 12 (novo) | Depende do passo 2. Instala o pin `pytest==<versão>` do `pyproject.toml` (função `pytest_pin`) no venv do bob de `S2_HOME` e roda, na raiz do checkout, `env -i HOME=$S2_HOME … PATH=<venv>/bin:$(tool_path) <venv>/bin/python -m pytest -q -p no:cacheprovider tests/test_hook.py` → sai `0` com `7 passed`. Imprime `verify-install: passo 12: tempo <s> s`. Roda nos dois modos (espelho e `VERIFY_REMOTE=1`). |
Passos 1, 9a e 9b: o projeto continua byte a byte igual (inclusive `.git/hooks`), porque o `bob setup` para antes do passo `hook` ou nem roda. Passo 5: os três projetos ganham o hook; nada a conferir lá.

## Códigos de saída
| Situação | Saída |
|---|---|
| `bob setup` com `HookPathError`, `ToolError` ou `OSError` no passo `hook` | `4` (resumo parcial, `bob doctor: not run`) |
| `bob setup` com hook `created`, `updated`, `unchanged`, `preserved` ou `preserved_hookspath` | o do `bob doctor` (como hoje) |
| Hook | o do `bob check` (CT1); o git aborta o push se ≠ `0` |
| Harness | `0` tudo ok; `1` no primeiro passo que falha |

## Fora do desenho
- Docs (`README.md:319-326`, `README.pt-BR.md`, `docs/guides/pre-push.md` e o espelho pt-BR): U8. Até lá, os docs seguem com o `cp` manual do estático, que continua funcionando; o bob preserva essa cópia (sem a marca) e avisa.
- Encadear hooks, gerenciar `core.hooksPath`, desinstalar o hook: fora de escopo (ADR 0016, alternativas rejeitadas).
- `bob update` (U7) e o texto `cli.setup` ("npm tools, skills"), que continua como está, igual ao que U3 e U4 fizeram.
