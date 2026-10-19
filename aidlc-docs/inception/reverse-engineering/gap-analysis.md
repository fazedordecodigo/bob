# 2.1 Reverse Engineering — Análise de lacunas (existe vs. falta)

Repo: `fazedordecodigo/bob`, `main` @ `d2e26bd` (2026-10-18 16:39 UTC-3). Base: `ideation/intent/intent.md`.
Evidência `arquivo:linha` nesse commit. O que não consegui verificar está marcado "Não verificado".

## Vereditos dos achados do Analista

### Achado 1 — versão do Node diverge: **Parcial**
- Existe divergência, mas não no requisito. É uma frase velha sobre a Action.
- `docs/getting-started/installation.md:15` diz que a Action "still installs Node `22.14.0`".
- A Action instala `22.18.0` (`.github/actions/bob/action.yml:45`).
- O requisito é `>=22.18.0 <23` em todos: `docs/getting-started/installation.md:10`, `docs/instalacao.md:10`, `README.pt-BR.md:62`, `package.json:6`, `src/bob_quality/doctor.py:62`.
- `docs/instalacao.md:127` e `README.pt-BR.md:338` dizem que a Action usa `22.18.0`. Batem com o código.

### Achado 2 — lista de ferramentas pinadas no README incompleta: **Confirmado**
- `README.pt-BR.md:70` e `README.md:70` citam só lizard, coverage, diff-cover, mutmut, import-linter, grimp (Python) e c8, vitest, jscpd, dependency-cruiser (npm).
- Faltam deptry, complexipy, bandit, vulture e PyYAML (`pyproject.toml:15`, `:18`, `:22-24`).
- Faltam eslint, eslint-plugin-sonarjs, knip e os dois do Stryker (`package.json:11-12`, `:14`, `:16-17`).
- `docs/getting-started/installation.md:26`, `:37` lista todas. `docs/instalacao.md:24`, `:35` também está incompleto (sem deptry, complexipy e as cinco npm).
- Achado novo: todos os docs dizem vitest `5.0.4`. O pin é `5.0.5` (`package.json:15`). Ver `technology-stack.md`.

### Achado 3 — instalador sem pasta de destino do Claude Code: **Confirmado**
- Alvos: só `copilot` (`.github/skills`), `devin` e `agents` (`.agents/skills`) (`src/bob_quality/install_skills.py:17-21`).
- `docs/adr/0004-empacotamento-quatro-agentes.md:27`: "Claude Code não tem alvo no instalador."
- `docs/getting-started/agents.md:38`: "The installer has no Claude Code target."
- Hoje o Claude Code só recebe as skills por plugin (`README.pt-BR.md:76-83`). Isso conflita com o critério 2.
- Fonte externa (não está no repo): a doc do Claude Code põe skills de projeto em `.claude/skills/<nome>/SKILL.md` (https://code.claude.com/docs/en/skills, lida em 2026-10-18).

## Issue #45 — wheel sem skills
- Aberta. Título "Ship skills inside the bob-quality wheel (post-MVP)". Criada em 2026-10-11 18:11 UTC-3.
- Corpo: hoje o `install_skills` precisa de `--source`; incluir as skills no wheel para instalar sem clone. Ainda cita LICENSE/NOTICE do Pocock, já desatualizado (`docs/adr/0004-empacotamento-quatro-agentes.md:31`).
- O que o `pyproject.toml` empacota hoje: o pacote `bob_quality` de `src/` (`pyproject.toml:39-40`) mais `schemas/*.json`, `hooks/*`, `package.json`, `package-lock.json`, `js/*` (`:42-43`).
- Não entram: `skills/`, `.claude-plugin/`, `.cursor-plugin/`, `AGENTS.md`.
- Confirmado no log do build do workflow `package` (run 39159800688): a lista "adding" do wheel não tem nenhum arquivo de skill nem de manifesto.
- Efeito: `install_skills` procura o manifesto em `parents[2]` do arquivo instalado (`src/bob_quality/install_skills.py:23-24`). Fora de um clone, sai `4` e pede `--source` (`:147-150`).

## Critérios de sucesso

| # | Critério | Existe | Falta |
|---|---|---|---|
| 1 | Um comando até `bob doctor` = 0 em ≤ 5 min | `bob doctor` e `--install` (`src/bob_quality/doctor.py:123-133`). Pacote instala de `git+https` (`.github/actions/bob/resolve_install.py:40`). | Não há comando único. **Hoje o doctor sai `4` em `main`** (vitest 5.0.4 vs 5.0.5; run 39159800688). Doctor exige gitleaks (`doctor.py:91-97`); nada o instala fora do CI. Decidido (Q1 A): o comando de instalação baixa e confere o gitleaks, dentro dos 5 min. Tempo de 5 min: Não verificado. |
| 2 | Skills no projeto para Cursor, Claude Code, Copilot e Devin, sem plugin | `install_skills` para `.agents/skills` e `.github/skills` (`install_skills.py:17-21`). | Alvo do Claude Code. Fonte das skills sem clone (issue #45). Leitura de `.agents/skills` pelo Cursor e de `.github/skills` pelo Copilot: só o comentário do repo afirma (`install_skills.py:15-16`); Não verificado na doc dos agentes. |
| 3 | `bob.yaml` válido (`bob check` ≠ 4 por config) | Esquema e validação (`src/bob_quality/config.py:311-317`). Padrões na classe `Config` (`:275-297`) e no README (`README.pt-BR.md:182-203`). | Gerador de `bob.yaml`. O padrão `paths.include: [src]` sai `4` num projeto sem `src/` (`config.py:428-434`). Decidido (Q2 B): padrões do README com `paths.include` derivado das pastas de código existentes. |
| 4 | Hook pre-push ativo e rodando `bob check` | Script do hook, empacotado no wheel (`src/bob_quality/hooks/pre-push:1-5`, `pyproject.toml:43`). | Instalação do hook (hoje `cp` manual, `README.pt-BR.md:321-324`). O hook chama `bob` pelo `PATH` (`pre-push:5`); com o `bob` num venv inativo no `git push`, falharia (inferência; Não verificado). |
| 5 | Atualizar: doctor = 0 e skills na versão nova | Reinstalar skills substitui as do manifesto (`install_skills.py:194-197`). | Comando de atualização. Não há tags nem releases no repo (`list_tags` vazio). Versão fixa `0.1.0` em `pyproject.toml:7` e `.claude-plugin/plugin.json:3`. Sem noção de "versão nova" além de `main`. |
| 6 | Nenhum clone manual | Install `git+https` usado pela Action (`resolve_install.py:40`). | Skills ainda exigem clone (`README.pt-BR.md:110`). Docs só descrevem caminho com clone (`docs/instalacao.md:5`). |

## Suposições

| # | Suposição | O que o código diz |
|---|---|---|
| S1 | Python e Node já presentes | Faixas: Python `>=3.10` (`pyproject.toml:10`), Node `>=22.18.0 <23` (`doctor.py:62`). O doctor também exige gitleaks 8.30.1 (`doctor.py:91-97`). Decidido (Q1 A): o gitleaks não é pré-requisito; o comando de instalação o instala, dentro dos 5 min. S1 segue válida para Python e Node. |
| S2 | Não sobrescrever `bob.yaml`/hook sem avisar | Não há gerador nem instalador de hook hoje. O `cp` documentado sobrescreve calado. O `install_skills` apaga e recopia pastas com o mesmo nome das skills do bob (`install_skills.py:194-197`); outras ficam (`README.pt-BR.md:110`). |
| S3 | Atualizar preserva `bob.yaml` e `.bob/waivers.yaml` | `install_skills` só escreve nas pastas de skills (`install_skills.py:98-100`, `:185-199`). Não há mecanismo de atualização para avaliar. |
| S4 | `bob.yaml` com os padrões do README | Os padrões do README batem com `Config` (`README.pt-BR.md:182-203`, `config.py:275-297`). Conflito com critério 3 em projeto sem `src/` (`config.py:428-434`). Decidido (Q2 B): S4 vale em tudo, menos `paths.include`, que vem das pastas de código existentes. |
| S5 | Linux e macOS | Hook em `/bin/sh` (`pre-push:1`). Instalador só stdlib (`install_skills.py:1-4`). A dica de instalação do gitleaks é só `linux_x64` (`doctor.py:95-96`). Com Q1 A, o comando precisa do binário de macOS também. macOS: Não verificado. |
| S6 | Projeto é repo git | O bob roda `git diff <base>...HEAD` (`README.pt-BR.md:162`). Hook fica em `.git/hooks` (`README.pt-BR.md:322`). |

## Riscos extras achados no código
- O doctor lê versões npm primeiro de `<cwd>/node_modules` e de `<cwd>/node_modules/.bin` (`src/bob_quality/doctor.py:358-360`, `:437-441`). Num projeto TypeScript com outro vitest ou eslint próprio, o doctor pode comparar a versão do projeto, não a do bob. Inferência do código; Não verificado em execução.
- Versões npm em duas fontes (`package.json:8-18` e `doctor.py:69-111`). Foi a causa da quebra do vitest. Um bump do Dependabot repete o problema.
- `bob doctor --install` roda `npm ci` dentro do pacote instalado ou no cache do usuário (`npm_tools.py:133-154`). Funciona num pip install de git: Não verificado.

## Decisões técnicas a tomar no 2.6
1. Mecanismo de distribuição do comando `bob` direto do GitHub (ex.: `pip`/`pipx`/`uv tool` com `git+https`, ou script). Sem PyPI (Q2 C). → ADR 0011, 0013.
2. Fonte das skills sem clone: levar `skills/` e o manifesto no wheel (issue #45) ou baixar do GitHub na instalação. → ADR 0010.
3. Forma do "comando único": subcomando novo de `bob` ou script. A ADR 0004 diz que o instalador não é subcomando (`docs/adr/0004-empacotamento-quatro-agentes.md:23`). Mudar pede nova ADR. → ADR 0012.
4. Alvo do Claude Code no instalador (`.claude/skills`, segundo a doc externa) e o conjunto padrão de alvos sem duplicar no Devin (`docs/adr/0004-empacotamento-quatro-agentes.md:35`). → ADR 0009.
5. Corrigir o pin do vitest no doctor e ter uma fonte única das versões npm (ler do `package.json` ou teste de paridade). → ADR 0008.
6. Instalação do hook: cópia, `core.hooksPath` ou wrapper; e como o hook acha o `bob` fora de um venv ativo. → ADR 0016, 0013.
7. Como não sobrescrever `bob.yaml`/hook existentes (S2) e como preservar na atualização (S3). → ADR 0017.
8. Instalação do gitleaks 8.30.1 pelo comando (Q1 A): URL e sha256 por plataforma (Linux e macOS; decidir arm64), pasta de destino do binário, como o doctor o acha no `PATH`, e caber nos 5 min. Hoje o pin, a URL e o sha256 só existem para `linux_x64` em `doctor.py:91-97`. → ADR 0014.
9. Noção de versão para "atualizar" (tag, ref de `main` ou versão do pacote). → ADR 0018, 0011.
10. Atualizar os docs: Node da Action, lista de pinadas, vitest 5.0.5, inputs da Action, e o gitleaks como parte do comando de instalação (não pré-requisito). → ADR 0020.
11. Derivação de `paths.include` (Q2 B): que pastas contam como "de código" (reaproveitar a detecção de `config.py:320-326` e `:410-414`?), excluir `paths.exclude`, e o fallback quando o projeto não tem nenhuma pasta de código. O `bob.yaml` gerado precisa passar em `config.py:428-434`. → ADR 0015.

Nota do 2.6 (2026-10-18): lista reordenada para 1..11, sem mudar o texto. Os números ficaram os mesmos porque `requirements.md` cita "decisão 4" e "decisão 11". Cada item aponta a ADR que o resolve em `../application-design/decisions.md`.

## Perguntas ao Emerson
- `reverse-engineering-questions.md`: 2 perguntas, respondidas (Emerson, via Maestro, 2026-10-18 17:12 UTC-3: "Aceito as recomendações: Q1 A, Q2 B.").
- Q1 A: o comando de instalação instala o gitleaks, dentro da meta de 5 min.
- Q2 B: `bob.yaml` gerado com os padrões do README e `paths.include` derivado das pastas de código existentes.
- Nenhuma pergunta aberta.
