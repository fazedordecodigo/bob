# U4 — u4-bob-yaml — Desenho funcional (3.1, Minimal)

Unit: U4 | Kind: library | Dona de: C05 (`src/bob_quality/init_config.py`) | Estende: C02 (passo `bob.yaml` do `bob setup`, CT3 ordem 6), harness (CT15: passo 5 novo; passos 7 e 8 conferem `bob.yaml` e `.bob/waivers.yaml`)
Contrato de que é dona: CT7. Consome: CT1, CT3, CT5, CT15 (U1).
ADR: 0015 (geração e regra de `paths.include`), 0017 (preservação, posse, idempotência).
Histórias e requisitos: US3.1 e US3.2 (dona; U5 e U7 contribuem para a US3.2); FR4.1–FR4.6; NFR4, NFR5.
Base lida: `fazedordecodigo/bob` `main` @ `0b4c6ec4e61f653fe8235b3ed20306a69ca46bcc` (#194, U3 fechada; leitura remota pelo cursor-github, sem clone). Data: 2026-10-20 15:3x (UTC-3).

## O que passa a existir
Quando o projeto ainda não tem `bob.yaml`, o `bob setup` cria um, com os padrões do README e um `paths.include` calculado a partir das pastas de código que o git lista. O texto é validado por `load_config` num temporário e só então entra por rename atômico. Se o `bob.yaml` já existe, o `bob setup` não toca no arquivo e o lista no resumo como preservado, e faz o mesmo com `.bob/waivers.yaml`. O harness ganha o passo 5, que roda três projetos (com `src/`, só `app/`, sem código) e confere que `bob check --base HEAD --gates crap,dry,deps` não sai `4`.

```
bob setup: projeto → runtimes → npm → gitleaks → skills → bob.yaml → [doctor] → resumo
  bob.yaml: existe (arquivo, link ou pasta)? → preserved (0 leituras, 0 escritas)
            senão: git ls-files → pastas de código → include → texto CT7 → bob.yaml.tmp-<pid>
                   → load_config(tmp) → os.replace → bob.yaml
  .bob/waivers.yaml existe? → só entra no resumo como preservado (nunca é lido nem escrito)
```

## Estado atual do repo (conferido @ 0b4c6ec)
| Ponto | Hoje | Onde |
|---|---|---|
| Gerador de `bob.yaml` | não existe (`src/bob_quality/init_config.py` ausente) | árvore da `main` |
| `bob setup` | `STEPS = (projeto, runtimes, npm, gitleaks, skills)`; `Status` já tem `preserved` | `setup_cmd.py:192-198`, `:28` |
| Modelo de passo com preservados e avisos | `step_skills` + `_skills_outcome`; erro de escrita em `_skills_write_error` | `setup_cmd.py:182-189`, `:366-385` |
| Falha com motivo de exceção | `_failed_reason(step, exc)` → `setup.step_reason` | `setup_cmd.py:324-325` |
| Esquema e validação | `_SCHEMA` `config.py:90-271`; `Config` (padrões) `:274-297`; `load_config(path, cwd)` `:311-317`; `_reject_missing_include` `:428-434`; `_reject_unknown` `:470-473` | `config.py` |
| Detecção | `_SUFFIX_LANGUAGE` (7 sufixos) `config.py:25-33`; `_excluded(relative, exclude)` `:417-425`; `DEFAULT_EXCLUDE` `:15` | `config.py` |
| Lista de arquivos do git | `_listed_files(cwd)`: `git ls-files -co --exclude-standard -z`; `OSError` → `ToolError(tool.missing git)`; saída ≠ 0 → `ToolError(git.ls_files_failed)` | `suite_fingerprint.py:49-62` |
| Padrões do README | bloco YAML em `README.pt-BR.md:182-204` (chaves `:183-203`) e `README.md:182-204`, idênticos; inclui `languages: [python]` | README |
| Mensagens do setup | `setup.*` em `messages.py:396-444` (en) e `:796-847` (pt-BR) | `messages.py` |
| Harness | `STEP_IDS='1 2 3 4 7 8 9a 9b'`; `new_project` cria `src/app.py`; passo 7 compara o `digest` do projeto; passo 8 confere 3 arquivos por sha e a linha `  preserved: .agents/skills/outra (not from bob)`; `run_selected` faz `3\|4\|7) ensure_2` | `scripts/verify-install.sh:4`, `:330-342`, `:822-886`, `:888-949`, `:1051-1076` |
| Testes ligados | `test_steps_follow_the_ct3_order` (`test_setup_cmd.py:295-303`); `test_setup_does_not_touch_the_project_package_files` roda os `STEPS` reais (`:906-936`); `test_step_ids_are_the_u1_and_u3_steps`, `_HELP` e o caso `--only 5` de `test_usage_errors_exit_1_before_preparing` (`test_verify_install.py:17-21`, `:86-87`, `:151-177`) | `tests/` |

## Regras de negócio
| # | Regra | Origem |
|---|---|---|
| R1 | `bob.yaml` existe quando `(project / "bob.yaml").exists() or (project / "bob.yaml").is_symlink()` (arquivo, pasta ou link, inclusive link quebrado). Nesse caso: `ConfigResult("preserved", ())`, sem rodar o git, sem ler e sem escrever. | CT7, FR4.6, ADR 0017 |
| R2 | Arquivos candidatos: `suite_fingerprint._listed_files(project)` (rastreados e não ignorados, `-co --exclude-standard -z`; mesma semântica do CT7 passo 1). `ToolError` dessa função propaga sem mudança. | CT7 passo 1, D3 |
| R3 | Um candidato conta como código só se: o sufixo (`Path(name).suffix`) é chave de `config._SUFFIX_LANGUAGE`; `project / name` é arquivo regular que existe (`is_file()`) e não é link (`not is_symlink()`); e `config._excluded(Path(name), tuple(DEFAULT_EXCLUDE))` é falso. | CT7 passos 2–3, I23 |
| R4 | Arquivo de código sem `/` no nome → "código na raiz". Senão, a pasta candidata é o 1º componente, se não começa com `.`. | CT7 passo 4 |
| R5 | `src` entre as candidatas → `("src",)`, `created`. Senão, há candidatas → `tuple(sorted(candidatas))` (ordem de código Unicode), `created`. Senão, código na raiz → `(".",)`, `created`. Senão → `(".",)`, `created_no_code`. | CT7 passo 5, ADR 0015 |
| R6 | Texto = CT7 exato (19 linhas, UTF-8, LF, termina em `\n`), sem `languages`; só a linha `  include: <INCLUDE>` varia. `<INCLUDE>` = `[` + itens unidos por `, ` + `]`. Item `.` → `"."`. Outro item fica sem aspas se `parse_yaml(f"[{item}]") == [item]`; senão (inclusive `yaml.YAMLError`) vai como `json.dumps(item, ensure_ascii=False)`. | CT7, I22 |
| R7 | Grava `project / f"bob.yaml.tmp-{os.getpid()}"` com `write_bytes(texto.encode("utf-8"))`, chama `load_config(tmp, project)` e faz `os.replace(tmp, project / "bob.yaml")`. Qualquer exceção nesses três passos: `tmp.unlink(missing_ok=True)` e a exceção sobe sem mudança (`ConfigError`, `OSError`). | CT7 passo 6, ADR 0015, ADR 0017 |
| R8 | `.bob/waivers.yaml`: o passo `bob.yaml` só confere a existência (mesma regra de R1) e, se existe, acrescenta o item preservado `setup.preserved_waivers` em qualquer estado. Nunca lê nem escreve o arquivo. | pronto 4, NFR5, ADR 0017, I24 |
| R9 | Passo `bob.yaml` (tabela abaixo). Não imprime nada; o `bob setup` imprime a linha do passo, os avisos e o resumo (CT3). | CT3 |
| R10 | Nenhuma pergunta ao dev; repetir não muda nenhum arquivo (o 2º `bob setup` acha o `bob.yaml` e cai em R1). | NFR4, R-S3 |

## Interface de `init_config.py` (CT7 + acréscimos compatíveis)
```python
CONFIG_NAME = "bob.yaml"
ConfigState = Literal["created", "preserved", "created_no_code"]

@dataclass(frozen=True)
class ConfigResult:
    state: ConfigState
    include: tuple[str, ...]          # vazio se preserved

def render_config(include: Sequence[str]) -> str: ...      # acréscimo (R6)
def write_default_config(project: Path) -> ConfigResult: ...  # CT7; ConfigError, OSError, ToolError sobem
```
Acréscimos ao CT7: `CONFIG_NAME` e `render_config`. Nenhum nome do CT7 muda. `write_default_config` também pode levantar `ToolError` (git, R2) e `OSError` (escrita, R7). O CT7 só cita `ConfigError`; esses dois são acréscimo compatível (I28).

## Passo `bob.yaml` no `bob setup` (CT3, ordem 6)
| Situação | `StepResult` |
|---|---|
| `created` | `installed`, `installed=(msg("setup.item_bob_yaml"),)`, `preserved=W` |
| `created_no_code` | `installed`, `installed=(msg("setup.item_bob_yaml"),)`, `preserved=W`, `warnings=(msg("setup.warn_no_code"),)` |
| `preserved` | `preserved`, `preserved=(msg("setup.preserved_bob_yaml"),) + W` |
| `ConfigError` | `failed`, `error=msg("setup.bob_yaml_invalid", detail=reason(exc))` |
| `ToolError` | `failed`, `error=_failed_reason("bob.yaml", exc)` (texto `bob.yaml: <motivo>`) |
| `OSError` | `failed`, `error=msg("setup.bob_yaml_write", detail=exc.strerror or type(exc).__name__)` |
`W` = `(msg("setup.preserved_waivers"),)` se `.bob/waivers.yaml` existe (R8), senão `()`.
`STEPS` = `projeto`, `runtimes`, `npm`, `gitleaks`, `skills`, `bob.yaml`.

## Mensagens (catálogo `messages.py`, en e pt-BR)
| Chave | en | pt-BR |
|---|---|---|
| `setup.item_bob_yaml` | `bob.yaml` | `bob.yaml` |
| `setup.preserved_bob_yaml` | `bob.yaml (already exists; not changed)` | `bob.yaml (já existe; sem mudanças)` |
| `setup.preserved_waivers` | `.bob/waivers.yaml (bob does not change it)` | `.bob/waivers.yaml (o bob não altera)` |
| `setup.warn_no_code` | `no code folder found; paths.include: ["."].` | `nenhuma pasta de código encontrada; paths.include: ["."].` |
| `setup.bob_yaml_invalid` | `bob.yaml: the generated file is invalid ({detail}). Open an issue.` | `bob.yaml: o arquivo gerado é inválido ({detail}). Abra uma issue.` |
| `setup.bob_yaml_write` | `bob.yaml: could not write bob.yaml ({detail}). Check the permissions.` | `bob.yaml: não consegui gravar bob.yaml ({detail}). Confira as permissões.` |

Na saída (en): `bob setup: bob.yaml: ok`; `bob setup: bob.yaml: warning: no code folder found; paths.include: ["."].`; no resumo, `  installed: …, bob.yaml`, `  preserved: bob.yaml (already exists; not changed)`, `  preserved: .bob/waivers.yaml (bob does not change it)`, `  warnings: no code folder found; paths.include: ["."].`

## Harness (CT15; passos 5, 7 e 8)
| Passo | Muda |
|---|---|
| 5 (novo) | Depende do passo 2 (`ensure_2`). Usa `S2_HOME`, com bob, npm e gitleaks já instalados. Três projetos novos em `$T/s5/<caso>`: `src` (`src/app.py`), `app` (`app/main.py`), `sem-codigo` (`README.md`), cada um com 1 commit. Para cada caso: o comando único sai `0`, com a última linha `  bob doctor: 0`; o `bob.yaml` é byte a byte igual a `expected_bob_yaml` com `[src]`, `[app]` ou `["."]`; a linha `bob setup: bob.yaml: warning: no code folder found; paths.include: ["."].` aparece só em `sem-codigo`; `bob check --base HEAD --gates crap,dry,deps`, rodado com o launcher de `S2_HOME`, sai ≠ `4`. Imprime `verify-install: passo 5: tempo <s> s`. |
| 7 | Além do `digest` de hoje: o stdout tem `  preserved: bob.yaml (already exists; not changed)`. |
| 8 | O projeto do passo ganha `bob.yaml` (`base: origin/main`, `paths:`, `  include: [src]`) e `.bob/waivers.yaml` (`# waivers do dev`), versionados. Os dois entram na conferência por sha, e o stdout tem as duas linhas `  preserved:`. |
| ids | `STEP_IDS='1 2 3 4 5 7 8 9a 9b'`; `run_selected` faz `3\|4\|5\|7) ensure_2`. |
Passos 1, 9a e 9b: o projeto continua byte a byte igual, porque o `bob setup` para antes do passo `bob.yaml` (node, gitleaks) ou nem roda (wheel). Não mudam.

## Códigos de saída
| Situação | Saída |
|---|---|
| `bob setup` com `ConfigError`, `ToolError` ou `OSError` no passo `bob.yaml` | `4` (resumo parcial, `bob doctor: not run`) |
| `bob setup` com `bob.yaml` criado ou preservado | o do `bob doctor` (como hoje) |
| `bob check` com o `bob.yaml` gerado | não sai `4` por configuração (FR4.4); o código vem dos gates |
| Harness | `0` tudo ok; `1` no primeiro passo que falha |

## Fora do desenho
- Hook pre-push (U5), atualização (U7) e o resto da US3.2. O item "hook próprio" do passo 8 é da U5.
- Adaptar `base` à branch padrão do projeto: não muda (ADR 0015, FR4.2).
- O comportamento dos gates com `include: ["."]` (código dos gates): fora da U4. O passo 5 só prova o código de saída (ver o risco R1 do plano).
- O texto `cli.setup` ("npm tools, skills") continua como está, igual ao que a U3 fez.
