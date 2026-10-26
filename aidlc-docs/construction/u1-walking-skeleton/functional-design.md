# U1 — u1-walking-skeleton — Desenho funcional (3.1 leve)

Unit: U1 | Kind: packaging | Dono de: C01 (`install.sh`), C02 (`bob setup`), C03 (skills), C04 (wheel), C13 (pastas do usuário)
Contratos de que é dona: CT1, CT2, CT3, CT4, CT5, CT6, CT12, CT14 (registro), CT15. Consome: CT8 (U2, já na `main`).
ADRs: 0009, 0010, 0011, 0012, 0013 (sem o perfil), 0017.
Base lida: `fazedordecodigo/bob` `main` @ `053dcaab7796f8885c4830ee3a5f6bf1fc75d65a` (#183 e #182 mergeados; leitura remota pontual, sem clone). Data: 2026-10-18 23:3x (UTC-3).

## O que passa a existir
Menor fatia ponta a ponta: um comando, rodado na raiz de um projeto git, baixa a release, confere o wheel, cria o venv do usuário, liga o launcher e roda `bob setup`, que instala as ferramentas npm, grava as skills em `.agents/skills` e termina com `bob doctor: 0`.

```
curl -fsSL <base>/latest/download/install.sh | sh
  install.sh: projeto → plataforma → python → node → ferramentas → versão → download → integridade → pacote → launcher → setup
    exec $BOB_HOME/bin/bob setup --lang <l>
      bob setup: projeto → runtimes → npm → skills → [doctor] → resumo
```

Ficam de fora (outras units): passo `perfil` do `install.sh` e a linha `perfil do shell` do resumo (U6); passo `gitleaks` do `bob setup` (U3; até lá o harness põe o gitleaks no `PATH`); passos `bob.yaml` (U4) e `hook` (U5); `bob update` e `bob --version` (U7); docs (U8); `release.yml` (U9).

## Estado atual do repo (conferido)
| Ponto | Hoje | Onde |
|---|---|---|
| Subcomandos | `check crap dry deps mutate report waive doctor`; `bob setup` não existe | `cli.py:62-127` |
| Teste da ajuda | lista fixa `{check,crap,dry,deps,mutate,report,waive,doctor}` | `tests/test_usage_exit.py:215-230` |
| Skills no wheel | não vão: `package-data` = `schemas/*.json`, `hooks/*`, `package.json`, `package-lock.json`, `js/*` | `pyproject.toml:39-40` |
| Fonte das skills | `--source` padrão = `Path(__file__).resolve().parents[2]` (só funciona no clone) | `install_skills.py:24`, `:95-99` |
| Alvo `agents` | já existe, `.agents/skills` | `install_skills.py:17-21` |
| `install.sh` do projeto | não existe; o único `install.sh` é o da action (`.github/actions/bob/install.sh`, bash, outro propósito) | árvore da `main` |
| Harness | `scripts/verify-install.sh` não existe; `scripts/` tem só `validate_cursor_plugin.py` e o schema | árvore da `main` |
| Doctor | lê as versões npm e o Node do `package.json` empacotado; npm só do prefixo do bob; `node` e `gitleaks` pelo `PATH` | `doctor.py` (pós-#183) |
| Prefixo npm no wheel | `npm_prefix()` acha `site-packages/bob_quality/package.json` (nome `bob-quality-tools`); `install_npm_dependencies` roda `npm ci --prefix` ali | `npm_tools.py` |
| mutmut | `also_copy` já inclui `scripts`, `skills`, `.claude-plugin`, `LICENSE` | `pyproject.toml:52-76` |

## Regras de negócio
| # | Regra | Origem |
|---|---|---|
| R1 | Uso normal instala sempre a última release publicada (`releases/latest`). `BOB_VERSION` só para harness, release-check e `bob update`; `--help` e mensagens não a oferecem, exceto a de valor inválido. | FR1.4, CT2, CT6, I8 |
| R2 | Os passos `projeto` a `ferramentas` não escrevem nada. Até `launcher`, 0 arquivos do projeto mudam. `versão`, `download` e `integridade` escrevem só no temporário. Falha de pré-requisito: `BOB_HOME` nem é criado. | US1.2 crit. 1 e 3, CT2 |
| R3 | O wheel só é usado depois de o sha256 bater com a linha dele no `SHA256SUMS` da mesma tag. Linha ausente = falha. Falha: `4`, nenhum `versions/<v>` novo. | NFR6, CT12, pronto 8 |
| R4 | Nada pede `sudo` nem senha. Tudo vai para `$BOB_HOME` e `~/.local/bin`. | NFR7, ADR 0013 |
| R5 | Layout do CT5: `versions/<X.Y.Z>/venv`, `.complete` (sha do wheel + `\n`) gravado por último, `current` trocado por `os.replace`, `bin/bob → ../current/venv/bin/bob`, `~/.local/bin/bob → $BOB_HOME/bin/bob`. `.complete` igual ao sha → reusa, não reinstala. | CT5, NFR4 |
| R6 | `BOB_HOME` = `$BOB_HOME` (absoluto) ou `${XDG_DATA_HOME}` absoluto `/bob-quality` ou `$HOME/.local/share/bob-quality`. `XDG_DATA_HOME` relativo é ignorado. `BOB_HOME` relativo é erro `4`. Mesmo cálculo no `install.sh` e em `user_dirs.bob_home()`. | CT5, CT6 |
| R7 | Faixas de Node e Python do `install.sh` = `engines.node` do `package.json` e `requires-python` do `pyproject.toml` (teste de paridade, I9). | ADR 0008, CT8, I9 |
| R8 | `bob setup` não pergunta nada, para no primeiro passo que falha, sai `4` nesse caso e, se todos passam, sai com o código do `bob doctor`. | CT3, FR1.5, FR7.2 |
| R9 | Skills só em `.agents/skills/<nome>/`, com os arquivos da skill + `LICENSE` + `.bob-version` (`X.Y.Z\n`). Nada em `.claude`, `.github`, `.cursor`, `.devin`. Sem symlink. | ADR 0009, CT4, FR3.2, FR3.3 |
| R10 | Posse: o bob só reescreve pasta com `.bob-version`. Pasta sem marcador, symlink, arquivo ou pasta de outro nome: não toca; vai para `preservado`. Pasta com marcador cujo nome saiu do manifesto: apaga. | ADR 0017, CT4, FR3.4 |
| R11 | Idempotência: segunda execução seguida → `0`, 0 arquivos do projeto alterados, 0 `npm ci`, 0 venv novo. | NFR4, US1.1 crit. 6 |
| R12 | Cópia do bob em `.claude/skills/<nome>` ou `.github/skills/<nome>` (pasta com `SKILL.md`, com ou sem `.bob-version`) → aviso de duplicata; não apaga. | ADR 0009, CT4 regra 6 ampliada (I10) |
| R13 | Toda falha é uma linha no stderr no formato CT1 `<prefixo>: <passo>: <o que falhou>. <ação>.`, em en (padrão) e pt-BR. | FR7.2, NFR9, CT1 |
| R14 | O `bob setup` não altera manifestos nem lockfiles do projeto (`package.json`, `node_modules`, lockfiles). | FR2.4, NFR5 |

## Fluxo `install.sh` (CT2, sem `perfil`)
| Passo | Faz | Falha (exit 4, uma linha CT1) |
|---|---|---|
| (início) | args (`--lang`, `--help`); idioma (`--lang` > `BOB_LANG` > `en`); `BOB_HOME` | uso inválido; idioma inválido; `BOB_HOME` relativo |
| `projeto` | `git` existe; `git rev-parse --show-toplevel` = `pwd -P` | git ausente; não é a raiz |
| `plataforma` | `uname -s` ∈ {Linux, Darwin}; `uname -m` ∈ {x86_64, amd64, aarch64, arm64} | SO/arquitetura fora |
| `python` | `python3` ≥ `PYTHON_FLOOR`; `import venv, ensurepip` | ausente; velho; sem venv |
| `node` | `node --version` = `vX.Y.Z`, `NODE_FLOOR ≤ v < NODE_BELOW`; `npm` existe | ausente; fora da faixa; sem npm |
| `ferramentas` | `curl`; `sha256sum` ou `shasum` | ausente |
| `versão` | `BOB_VERSION` (se definida, valida) ou API `releases/latest` → `tag_name` | valor inválido; URL base proibida; API falhou |
| `download` | wheel e `SHA256SUMS` da tag para o temporário | 404 (release incompleta) ou outro erro |
| `integridade` | sha256 do wheel = linha do `SHA256SUMS` | não confere / linha ausente |
| `pacote` | venv por versão + `pip install` do wheel + `.complete`; ou reusa | pip/venv falhou (apaga `versions/<v>`) |
| `launcher` | `current`, `bin/bob`, `~/.local/bin/bob` (avisa se for de outro) | não conseguiu criar |
| `setup` | apaga o temporário; `exec "$BOB_HOME/bin/bob" setup --lang <l> </dev/null` | código do `bob setup` |

## Fluxo `bob setup` (CT3)
1. `bob_home()`; `BOB_HOME` relativo → erro, `4`, nada roda.
2. Para cada `(id, passo)` de `STEPS` (`projeto`, `runtimes`, `npm`, `skills`): roda; imprime `bob setup: <id>: ok`; `failed` → para.
3. Se todos passaram: fase final `doctor` (fora de `STEPS`, I11): `run_doctor(install=False, lang)`; a saída do doctor vai para o stdout como hoje.
4. Resumo (stdout). Última linha `  bob doctor: <0|4>`, ou `  bob doctor: not run` / `não rodou` se parou antes.

| Passo | Faz | `installed` | `preserved` / avisos | Falha |
|---|---|---|---|---|
| `projeto` | `git rev-parse --show-toplevel` (no `cwd`) = `cwd` resolvido | — | — | `projeto: <dir> não é a raiz de um repositório git. Rode na raiz do projeto.` |
| `runtimes` | Python ≥ piso de `Requires-Python`; `node --version` aceito por `node_admits(node_pin(), …)` | — | — | python velho; node ausente; node fora; `package.json` empacotado ilegível |
| `npm` | se toda dependência de `pinned_npm_versions()` já está em `npm_prefix()` na versão exata → nada; senão `install_npm_dependencies(lang)` | `ferramentas npm` | — | `npm: npm ci falhou. Rode <comando> e veja a saída acima.` |
| `skills` | `install_project_skills(project, version)` | `skills (<nomes>) em .agents/skills` | alheias, sem marcador, symlink, arquivo; avisos de sem-marcador e de duplicata | `skills: não consegui gravar <caminho> (<erro>). Confira as permissões.`; manifesto inválido |
| (doctor) | `run_doctor(install=False, lang)` | — | — | código vira o final |

## Skills no projeto (`install_project_skills`, CT4)
| Situação em `.agents/skills/<x>` | Ação | Resultado |
|---|---|---|
| `<x>` do manifesto, não existe | cria (temporário + `os.replace`) | `installed` |
| `<x>` do manifesto, pasta com `.bob-version`, conteúdo igual ao esperado | nada (0 escritas) | `unchanged` |
| `<x>` do manifesto, pasta com `.bob-version`, algum arquivo difere ou sobra | reescreve inteira | `installed` |
| `<x>` do manifesto, pasta sem `.bob-version` | nada | `preserved` + `unmarked` + aviso |
| `<x>` do manifesto, symlink ou arquivo | nada | `preserved` |
| `<x>` fora do manifesto, pasta com `.bob-version` | apaga (skill aposentada) | — |
| `<x>` fora do manifesto, qualquer outra coisa | nada | `preserved` |
| `.<x>.bob-tmp-<pid>` (sobra de execução interrompida) | apaga | — |

"Conteúdo esperado" = cada arquivo regular da pasta da skill na fonte (caminho relativo → bytes) + `LICENSE` (o mais próximo, como `_attribution`) + `.bob-version` = `"<versão>\n"`. Igual = mesmo conjunto de caminhos e mesmos bytes, sem symlink dentro.

## Wheel (C04, ADR 0010)
- `src/bob_quality/plugin/` com três symlinks versionados: `.claude-plugin → ../../../.claude-plugin`, `skills → ../../../skills`, `LICENSE → ../../../LICENSE`.
- `package-data` ganha `plugin/.claude-plugin/plugin.json`, `plugin/skills/**/*`, `plugin/LICENSE`.
- Fonte padrão do instalador de skills: `PLUGIN_ROOT` se tem `.claude-plugin/plugin.json` (clone/editável); senão `bob_quality/plugin/` (wheel).
- Conferido no box em 2026-10-18 23:2x (UTC-3), com um pacote mínimo de mesmo layout e setuptools 84.0.0 (build isolado): `python -m build` (sdist e wheel) segue os symlinks de diretório e de arquivo; o wheel leva `plugin/.claude-plugin/plugin.json`, `plugin/LICENSE` e `plugin/skills/<n>/SKILL.md`. O teste do wheel (T1) prova no repo real.

## Códigos de saída
| Comando | `0` | `4` | `1` |
|---|---|---|---|
| `install.sh` | `bob setup` saiu 0 | uso, pré-requisito, rede, integridade, pacote, launcher, ou o `4` do `bob setup` | — |
| `bob setup` | todos os passos ok e doctor `0` | passo falhou ou doctor `4` | — |
| `scripts/verify-install.sh` | todos os passos pedidos passaram | — | uso inválido, preparo falhou ou primeiro passo que falhou |

## Fora do desenho
- `perfil` (U6), `gitleaks` no `bob setup` (U3), `bob.yaml` (U4), hook (U5), `bob --version`/`bob update` (U7), docs e prompt de IA (U8), `release.yml` e matriz (U9).
- Fixture do passo 8 só com skill alheia e `package.json`/`node_modules` com vitest 4.1.0; U4 e U5 acrescentam `bob.yaml`, `.bob/waivers.yaml` e hook.
- macOS e arm64: o código cobre (`shasum`, `uname`), mas a prova automática é só Linux x64 (U9 roda a matriz). NFR3 fica com U9.
