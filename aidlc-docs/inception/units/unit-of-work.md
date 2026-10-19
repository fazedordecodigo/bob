# 2.7 Units — Unidades de trabalho

Projeto: bob. Profundidade: Minimal. Autor: Arquiteto Técnico. Data: 2026-10-18 (UTC-3).
Insumos (aprovados, só leitura): intent, 2.1, `requirements.md` (34 FR, 9 NFR, RA1), `stories.md` (13 US), 2.6 (C01–C13, ADR 0008–0020, `verification-command.md`).
Ordem de entrega e prioridade: **não** decididas aqui (são do Maestro, no 2.9). Aqui só há dependências (`unit-of-work-dependency.md`).

## Convenções
- **Dono**: cada componente C01–C13 tem exatamente uma unit dona. A dona cria o componente e fixa a interface dele.
- **Estende**: uma unit pode acrescentar um comportamento pequeno a um componente de outra dona, só pela interface que a dona fixou (ex.: um passo novo no `bob setup`). Toda extensão está listada e gera aresta no DAG para a dona.
- **Passos**: números do Comando de Verificação (`verification-command.md` do 2.6, tabela "Passos"). "parcial" = só os critérios ditos.
- **Pronto** de toda unit inclui: `pytest` verde e todos os passos do `scripts/verify-install.sh` já existentes seguem passando (sem regressão).

## Ajuste ao 2.6 (sem editar o 2.6)
- `scripts/verify-install.sh` aparece no 2.6 como arquivo do C11. Ele vira **infraestrutura de verificação compartilhada**: nasce no U1 (espelho local de release + passos do U1), e cada unit acrescenta seus passos. O C11 (U9) fica com `release.yml` e roda o script na matriz.
- Motivo: o walking skeleton precisa ser provado pelo Comando de Verificação antes de existir o workflow de release.
- O formato de release que o espelho local imita (ADR 0011) é fixado pelo U1 (lado consumidor, C01). O U9 o produz igual.

---

## U1 — u1-walking-skeleton
- **Kind:** packaging
- **Dono de:** C01 (`install.sh`), C02 (`bob setup`), C03 (instalador de skills), C04 (wheel com skills), C13 (pastas do usuário).
- **Estende:** nada.
- **Escopo:**
  - `install.sh`: plataforma, Python, Node, versão (`releases/latest` ou `BOB_VERSION`, via `BOB_RELEASES_URL`), download e sha256 do wheel contra `SHA256SUMS`, venv por versão, `current`, `BOB_HOME/bin/bob`, `~/.local/bin/bob`, `exec bob setup`.
  - `bob setup` com os passos `projeto → runtimes → npm → skills → doctor → resumo` e o registro de passos que U3, U4, U5 usam.
  - Skills só em `.agents/skills` (alvo `agents`), fonte = pacote, `.bob-version`, posse, idempotência, aviso de cópia em `.claude/skills`/`.github/skills`.
  - Wheel com `plugin/` (skills, manifesto, `LICENSE`) e teste do wheel.
  - `user_dirs.py` e o mesmo cálculo no `install.sh`, com teste de paridade.
  - `scripts/verify-install.sh` com espelho local (wheel + `SHA256SUMS` + `install.sh` + `releases/latest` falso).
- **Histórias:** US1.1, US1.2, US2.1, US6.1. Contribui: US1.4 (crit. 1), US3.2 (skills alheias), US7.2 (crit. 1).
- **FR:** FR1.1, FR1.2, FR1.3, FR1.4, FR1.5, FR2.4, FR3.1, FR3.2, FR3.3, FR3.4, FR7.1, FR7.2, FR7.3.
- **NFR:** NFR1, NFR2, NFR3, NFR4, NFR5, NFR6 (wheel), NFR7, NFR9.
- **ADRs:** 0009, 0010, 0011, 0012, 0013 (sem a parte do perfil), 0017.
- **Pronto quando:**
  1. Num projeto novo, o comando único (pelo espelho local) sai `0` e o resumo termina em `bob doctor: 0`. O gitleaks 8.30.1 é posto no `PATH` pelo harness até o U3 existir (o doctor já o acha pelo `PATH`, `doctor.py:437-441`).
  2. Duração ≤ 300 s no Linux x64 (as outras plataformas: U9).
  3. Existem `.agents/skills/{bob-check,harden,review-report}/SKILL.md` e `.bob-version`. Nada do bob em `.claude`, `.github`, `.cursor`, `.devin`.
  4. Node 20.0.0 falso: sai ≠ 0, cita `node`, a versão achada e `>=22.18.0 <23`; 0 arquivos do projeto mudam.
  5. Log do `sudo` falso vazio.
  6. Rodar de novo: sai `0`, 0 arquivos do projeto mudam.
  7. Skill alheia em `.agents/skills/outra/` fica com o mesmo hash; o resumo lista como preservada.
  8. Wheel com sha256 errado no espelho: sai `4`, cita "integridade", nenhum venv novo.
  9. O teste do wheel acha as três `SKILL.md`, o `plugin.json` e o `LICENSE`.
- **Passos:** 1, 2 (parcial: saída 0, doctor 0, ≤ 300 s, sem `git clone`), 3, 4, 7, 8 (parcial: skill alheia, `package.json` com 0 bytes alterados). Mais o caso "wheel adulterado" (pronto 8), que entra no passo 9 como caso (b).

## U2 — u2-doctor-fonte-unica
- **Kind:** library
- **Dono de:** C08 (`bob doctor`), C09 (fonte das versões npm).
- **Estende:** nada.
- **Escopo:** correção **P1**. `pinned_npm_versions()` e `node_range()` leem o `package.json` empacotado; `NpmPin` perde `expected` (`doctor.py:70` tem `5.0.4`, `package.json:15` tem `5.0.5`); `tests/test_npm_pin.py` perde a cópia fixa e confere lock = `package.json`; o doctor deixa de olhar `cwd/node_modules` (`doctor.py:358-360`).
- **Histórias:** US1.4. Contribui: US1.1 (crit. 5).
- **FR:** FR2.1, FR2.5.
- **NFR:** NFR5.
- **ADRs:** 0008, 0019.
- **Pronto quando:**
  1. `rg` não acha versão npm literal em `src/bob_quality/doctor.py` nem em `tests/test_npm_pin.py`.
  2. `bob doctor` sai `0` com vitest 5.0.5 instalado no prefixo do bob (o caso que falhou no job 117770515138).
  3. Teste: `package-lock.json` diverge do `package.json` → teste falha (paridade).
  4. Projeto com vitest 4.x em `node_modules` do cwd: `bob doctor` sai `0` e mostra a versão do bob.
  5. O job de empacotamento da `main` volta a passar.
- **Passos:** `pytest` (paridade e doctor); 8 (parcial: vitest do projeto, `bob doctor` = 0).

## U3 — u3-gitleaks
- **Kind:** library
- **Dono de:** C07 (instalador do gitleaks).
- **Estende:** C02 (passo `gitleaks`), C08 (gitleaks em `BOB_HOME/bin` antes do `PATH`; `--install` instala o gitleaks; tabela importada do C07).
- **Escopo:** tabela das 4 plataformas e sha256 (ADR 0014), `BOB_GITLEAKS_BASE_URL`, download temporário, conferência, extração só do membro `gitleaks`, instalação em `BOB_HOME/tools/gitleaks/8.30.1/`, link em `BOB_HOME/bin/gitleaks`.
- **Histórias:** US1.3. Contribui: US1.1 (crit. 1 e 5 sem fixture).
- **FR:** FR2.2, FR2.3.
- **NFR:** NFR6, NFR1 (tempo com download), NFR3, NFR9.
- **ADRs:** 0014.
- **Pronto quando:**
  1. Teste: a tabela tem exatamente os 4 assets com os sha256 da ADR 0014.
  2. Projeto novo sem gitleaks no `PATH`: o passo 2 passa sem fixture, e `BOB_HOME/bin/gitleaks version` = 8.30.1.
  3. Tar.gz adulterado: sai `4`, cita `gitleaks` e "sha256", `BOB_HOME/tools/gitleaks` não existe.
  4. Segunda execução não baixa de novo (0 requisições ao servidor local).
- **Passos:** 2 (completo, sem fixture), 7, 9 (caso a).

## U4 — u4-bob-yaml
- **Kind:** library
- **Dono de:** C05 (gerador de `bob.yaml`).
- **Estende:** C02 (passo `bob.yaml`).
- **Escopo:** regra de `paths.include` da ADR 0015, texto fixo com os padrões do README, validação com `load_config` e rename atômico, preservação de `bob.yaml` existente.
- **Histórias:** US3.1, US3.2 (dona; U5 contribui com o hook, U7 com a atualização).
- **FR:** FR4.1, FR4.2, FR4.3, FR4.4, FR4.5, FR4.6.
- **NFR:** NFR4, NFR5.
- **ADRs:** 0015, 0017.
- **Pronto quando:**
  1. Três projetos (com `src/`; só `app/`; sem código): `paths.include` = `[src]`, `[app]`, `["."]`; `bob check --base HEAD --gates crap,dry,deps` ≠ `4` nos três.
  2. Aviso "nenhuma pasta de código" só no terceiro.
  3. Todas as outras chaves iguais ao README (`README.pt-BR.md:182-203`), sem `languages`.
  4. `bob.yaml` e `.bob/waivers.yaml` existentes: mesmo hash; resumo lista como preservados.
- **Passos:** 5, 7, 8 (parcial: `bob.yaml`, waivers).

## U5 — u5-hook-pre-push
- **Kind:** library
- **Dono de:** C06 (instalador do hook).
- **Estende:** C02 (passo `hook`).
- **Escopo:** template com `# managed-by: bob-quality` e caminho absoluto de `BOB_HOME/bin/bob`; destino por `git rev-parse --git-path hooks`; hook alheio e `core.hooksPath` preservados com aviso.
- **Histórias:** US4.1. Contribui: US3.2 (hook).
- **FR:** FR5.1, FR5.2, FR5.3.
- **NFR:** NFR8, NFR4, NFR5.
- **ADRs:** 0016, 0017.
- **Pronto quando:**
  1. `git push` para remoto bare com `env -i HOME=$HOME PATH=/usr/bin:/bin` dispara o hook e roda `bob check --gates crap,dry,deps`.
  2. `tests/test_hook.py` passa em < 60 s.
  3. Hook alheio: mesmo hash, aviso no resumo. `core.hooksPath` definido: nada gravado, aviso com a linha.
- **Passos:** 6, 7, 8 (parcial: hook), 12.

## U6 — u6-perfil-shell
- **Kind:** packaging
- **Dono de:** nenhum componente.
- **Estende:** C01 (passo `perfil` do `install.sh`), C02 (linha `perfil do shell` do resumo, por `BOB_INSTALL_PROFILE`).
- **Escopo:** regra da ADR 0013 (Q1 A do 2.6): detecção por `$SHELL`, linha marcada única, criação do perfil ausente, aviso sem falha.
- **Histórias:** contribui US1.1 (crit. 2), US6.1 (crit. 1).
- **FR:** contribui FR1.1 (comando `bob` disponível), FR7.1.
- **NFR:** NFR2, NFR4, NFR5, NFR7, NFR9.
- **ADRs:** 0013 (parte do perfil).
- **Pronto quando:** os cinco casos (a)–(e) do passo 13 passam, com `grep -c 'managed-by: bob-quality'` = `1` depois de duas execuções.
- **Passos:** 13.

## U7 — u7-update-versao
- **Kind:** library
- **Dono de:** C10 (`bob update` e `bob --version`).
- **Estende:** C08 (linha informativa "skills do projeto", lida de `.agents/skills/*/.bob-version`).
- **Escopo:** consulta à última release publicada, comparação `vX.Y.Z`, download e conferência do `install.sh` da tag nova, execução com `BOB_VERSION`; `bob --version` em duas linhas.
- **Histórias:** US5.1, US5.2, US7.2. Contribui: US3.2 (crit. 3, na atualização).
- **FR:** FR6.1, FR6.2, FR6.3, FR6.4, FR6.5.
- **NFR:** NFR2, NFR4, NFR5, NFR9.
- **ADRs:** 0018, 0011 (API `releases/latest`).
- **Pronto quando:**
  1. Espelho com v-antiga instalada, v-nova `latest` e uma pré-release mais nova: `bob update` sai `0`; `bob --version` mostra v-nova nas duas linhas; `.bob-version` = v-nova; `bob.yaml`, waivers, hook e skill alheia com mesmo hash; `bob doctor` = 0.
  2. `bob update` de novo: sai `0`, "já está na release mais nova", 0 arquivos mudam.
  3. Rascunho mais novo no espelho (fora do `latest`): nada muda.
- **Passos:** 2 (parcial: `bob --version` = versão da release), 10, 11.

## U8 — u8-docs
- **Kind:** spec (documentação do usuário)
- **Dono de:** C12 (docs de instalação).
- **Estende:** nada.
- **Escopo:** README pt-BR e en, `docs/instalacao.md`, `docs/getting-started/installation.md`, `docs/getting-started/agents.md` (pasta única `.agents/skills`, RA1 do Claude Code), `docs/guides/pre-push.md`; `tests/test_docs_pins.py`. Adendo A1 (L1): prompt de IA sem `install.sh` em `docs/install-prompt.en.md` e `docs/install-prompt.pt-BR.md` (CT18), seção "Alternativa" nos 4 docs de instalação (CT17) e passo 14 do `scripts/verify-install.sh` (CT15).
- **Histórias:** US7.1, US1.5 (A1).
- **FR:** FR8.1, FR8.2, FR8.3; A1: FR1.6, FR1.7, FR1.8, FR8.4, FR8.5.
- **NFR:** A1: NFR10, NFR11.
- **ADRs:** 0020.
- **Pronto quando:**
  1. O primeiro caminho de instalação nos 6 docs é o comando único (sem clone, sem plugin).
  2. `tests/test_docs_pins.py`: 100% das versões citadas batem com `pyproject.toml` e `package.json` (inclui vitest 5.0.5 e Node `>=22.18.0 <23`).
  3. Os docs dizem que o gitleaks vem pelo comando e explicam `bob update` e `bob --version`.
  4. (A1) Nos 4 docs de instalação, o comando único vem antes da seção "Alternativa", que aparece 1 vez e aponta o prompt no idioma do doc (CT17, FR8.4).
  5. (A1) `docs/install-prompt.en.md` e `.pt-BR.md` existem, com blocos iguais byte a byte; os 11 itens de paridade do CT18 passam em `tests/test_docs_pins.py` (FR1.6, FR1.8, FR8.5, NFR11: 0 blocos com `install.sh` ou `sudo`).
  6. (A1) Passo 14 do harness passa: manifesto A (`install.sh`) = manifesto B (prompt), `bob doctor` = 0 nos dois, 0 pedidos de `install.sh` no log do espelho, 2ª execução sem mudança (FR1.7, NFR10, NFR11).
- **Passos:** `pytest` (`tests/test_docs_pins.py`); 14.
- **Por que o passo 14 é da U8:** a U8 produz o prompt (CT18) e o passo 14 prova exatamente o prompt contra o `install.sh`. A U8 depende de U1–U7, então o `install.sh`, o `bob setup` completo, o gitleaks e o perfil já existem quando ela entra; o passo é acrescentado ao harness do U1, como as outras units fazem (CT15). Sem aresta nova.

## U9 — u9-release-v0-1-0
- **Kind:** packaging
- **Dono de:** C11 (workflow `release`).
- **Estende:** nada.
- **Escopo:** `.github/workflows/release.yml` (`workflow_dispatch`, inputs `tag`, `prerelease` (padrão `true`) e `dry_run`); confere `pyproject.toml` = tag; build, `twine check --strict`, `bob doctor`, `scripts/verify-install.sh` na matriz Linux/macOS × x64/arm64; gera `SHA256SUMS`; cria a release com `install.sh`, wheel e `SHA256SUMS`. Modelo `docs/release-checks/TEMPLATE.md` e `docs/release-checks/v0.1.0.md` com as linhas dos 5 agentes. ADR 0008–0020 viram `docs/adr/00NN-*.md`.
- **Histórias:** contribui US7.2 (publicar como pré-release), US1.1 (crit. 1 em cada plataforma), US1.5 (crit. 7: prompt conferido com 1 agente real por release; A1).
- **FR:** contribui FR1.2, FR1.4.
- **NFR:** NFR3, NFR1 (matriz); contribui NFR10, NFR11 (passo 14 na matriz e item "Prompt de IA" do release-check; A1).
- **ADRs:** 0011.
- **Pronto quando:**
  1. Rodado com `dry_run: true` (não cria tag nem release), o workflow passa nos 4 runners, e o artefato tem exatamente `install.sh`, `bob_quality-0.1.0-py3-none-any.whl` e `SHA256SUMS`, com `sha256sum -c SHA256SUMS` = OK.
  2. Tag diferente de `pyproject.toml`: o workflow para antes de criar release.
  3. `docs/release-checks/v0.1.0.md` existe, com as partes automáticas preenchidas, as 5 linhas manuais (Cursor, Claude Code com RA1, Copilot, Devin CLI, Devin web) e a linha "Prompt de IA" (CT13/CT18; A1) a preencher.
  4. ADRs 0008–0020 em `docs/adr/`.
  5. `docs/release-checks/v0.1.0.md` traz o roteiro abaixo (passos E1–E6), com os comandos exatos.
  6. **Pronto para o Emerson disparar.** O disparo e a publicação são dele (P2).
- **Passos:** todos (1–14) na matriz, mais a verificação manual por release (inclui o item "Prompt de IA"). No passo 10, o espelho local também roda o comando único num `HOME` novo e confere que ele instala a v-nova publicada, não a pré-release mais nova (US7.2 crit. 1; crit. 2 já está no passo 10/11).

### Fluxo da release v0.1.0 (Q1 A, `units-questions.md`)
Feito pelo Emerson, depois do pronto do U9. Nenhum agente dispara nem publica.

| # | Quem | O que | Prova |
|---|---|---|---|
| E1 | Emerson | Dispara `release.yml` com `tag: v0.1.0`, `prerelease: true`, `dry_run: false` | release `v0.1.0` criada como pré-release, com os 3 assets |
| E2 | Emerson | Confere que a pré-release **não** é a última release: `curl -s -o /dev/null -w '%{http_code}' https://api.github.com/repos/fazedordecodigo/bob/releases/latest` | `404` (ainda não há release publicada). A API devolve só "the most recent non-prerelease, non-draft release" (ADR 0011) |
| E3 | Emerson | Num projeto novo (R-S8): `curl -fsSL https://github.com/fazedordecodigo/bob/releases/download/v0.1.0/install.sh \| BOB_VERSION=v0.1.0 sh` | sai `0`, `bob doctor: 0`, `bob --version` = `0.1.0` |
| E4 | Emerson | Verificação manual nos 5 agentes, nesse projeto: Cursor, Claude Code (sob RA1 / ADR 0009 Risco 1), GitHub Copilot, Devin CLI, Devin web | evidência em `docs/release-checks/v0.1.0.md` (data UTC-3, versão do agente, saída ou captura) |
| E5 | Emerson | Se E3 e E4 passam (Claude Code registrado como está, por RA1): promove | ver "Promover" |
| E6 | Emerson | Depois de promover: repete E2 e baixa os assets de novo | E2 dá `200` com `tag_name` = `v0.1.0`; `sha256sum -c SHA256SUMS` = OK; `SHA256SUMS` igual ao da pré-release |

**Promover (E5).**
- Edita a release existente, sem rebuild e sem novo upload. Assets e `SHA256SUMS` ficam idênticos.
- Pela interface: editar a release `v0.1.0`, desmarcar "Set as a pre-release", marcar "Set as the latest release", salvar.
- Ou pela linha de comando: `gh release edit v0.1.0 --repo fazedordecodigo/bob --prerelease=false --latest`.
- A tag não muda. O workflow não roda de novo.

**Se E3 ou E4 falhar.**
- Não promove. A `v0.1.0` fica como pré-release; nenhum Dev a recebe pelo comando único (E2 segue `404`).
- A falha vai para `docs/release-checks/v0.1.0.md` e vira issue.
- A correção entra na `main` e sai como nova pré-release com tag nova (`v0.1.1`, com `pyproject.toml` = `0.1.1`). Tags não são reaproveitadas. O fluxo recomeça em E1.
- Exceção por RA1: o Claude Code não listar as skills não bloqueia a promoção. É registrado como está e levado ao Emerson (ADR 0009). Para os outros 4 agentes, a meta não muda: falha bloqueia.
- Apagar a pré-release falhada é decisão do Emerson; o fluxo não exige.

## Registro
- Correção L1 (2026-10-18 20:29 UTC-3; origem: `verification/phase-check-inception.md`, lacuna L1, via Maestro; Emerson aprovou o 2.9 e os passos 1–14 às 20:28 UTC-3): Adendo A1 (US1.5; FR1.6, FR1.7, FR1.8, FR8.4, FR8.5; NFR10, NFR11) e passo 14 trazidos do 2.8 (CT15, CT17, CT18) para o 2.7. DAG sem mudança. Mudou: U8 (escopo, US, FR, NFR, pronto 4–6, passo 14 e justificativa), U9 (US1.5 crit. 7, NFR10/NFR11, release-check com "Prompt de IA", passos 1–14).
