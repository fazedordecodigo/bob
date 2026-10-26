# 3.6 Build and Test — Rastreabilidade Cruzada Final (`cross-unit-traceability.md`)

- **Projeto:** `bob` (`fazedordecodigo/bob`)
- **Estágio:** 3.6 Build and Test (Passo 10 — *Cross-Unit Final Coverage Gate*)
- **Fonte:** `inception/units/traceability.json`, `inception/requirements/requirements.md`, `inception/user-stories/stories.md`, `inception/contracts/contract-summary.md` e verificações de PRs de `U1..U9` + `3.6 T1/T2`
- **Veredito do Portão de Cobertura Cruzada:** **PASS (`Atende` — 0 elementos sem cobertura)**
- **Data:** 2026-10-24 (America/Sao_Paulo, UTC-3)

---

## 1. Resumo Executivo da Cobertura

| Dimensão | Total | Construídos e Verificados (`Built & Verified`) | `N/A` | Descobertos (`Uncovered`) | Veredito |
|---|---:|---:|---:|---:|---|
| Requisitos Funcionais (`FR1.1..FR8.5`) | 39 | 39 | 0 | 0 | **PASS** |
| Requisitos Não Funcionais do Projeto (`NFR1..NFR11`) | 11 | 11 | 0 | 0 | **PASS** |
| Metas NFR por Unit (`U1-N*..U9-N*`) | 128 | 128 | 0 | 0 | **PASS** |
| Histórias de Usuário (`US1.1..US7.2`) | 14 | 14 | 0 | 0 | **PASS** |
| Contratos (`CT1..CT18`) | 18 | 18 | 0 | 0 | **PASS** |
| Unidades de Trabalho (`U1..U9`) | 9 | 9 (`completed`) | 0 | 0 | **PASS** |
| Especificações de Tarefa (`ETs`) | 34 (`32` de `U1..U9` + `2` de `3.6`) | 34 (`merged`) | 0 | 0 | **PASS** |

---

## 2. Matriz por Requisito Funcional (`FR1.1` a `FR8.5`)

| ID | Descrição resumida | Unit(s) | Tarefas (`ET`) | PR(s) | Arquivos-alvo principais | Testes / Passos do Harness | Status |
|---|---|---|---|---|---|---|---|
| `FR1.1` | Um único comando na raiz configura `bob`, ferramentas, skills, `bob.yaml`, hook e perfil | U1, U6, U9 | U1-T3, U1-T4, U1-T5, U6-T1..T4, U9-T1 | #187, #188, #189, #204, #205, #207, #210, #216 | `scripts/install.sh`, `src/bob_quality/setup_cmd.py` | `tests/test_install_sh.py`, `tests/test_setup_cmd.py`, `verify-install.sh` passos `2`, `13` | `Built` |
| `FR1.2` | Obtenção direta do GitHub Releases sem clonar repo nem usar PyPI para `bob-quality` | U1, U8, U9 | U1-T1, U1-T4, U8-T2, U9-T1 | #184, #188, #211, #216 | `scripts/install.sh`, `.github/workflows/release.yml` | `tests/test_package.py`, `tests/test_install_sh.py`, `tests/test_release_workflow.py`, passos `2`, `14` | `Built` |
| `FR1.3` | Nenhum plugin nativo necessário em nenhum passo | U1, U8 | U1-T1, U1-T2, U1-T4, U8-T2 | #184, #185, #186, #188, #211 | `src/bob_quality/install_skills.py`, `scripts/install.sh` | `tests/test_project_skills.py`, `tests/test_docs_pins.py`, passos `2`, `4` | `Built` |
| `FR1.4` | Instala a última release publicada (exclui pré-release e rascunho) | U1, U8, U9 | U1-T4, U1-T5, U8-T1, U8-T2, U9-T1, U9-T2 | #188, #189, #209, #211, #214, #216 | `scripts/install.sh`, `.github/workflows/release.yml`, `docs/release-checks.md` | `tests/test_install_sh.py`, `tests/test_release_workflow.py`, `tests/test_release_checks.py`, passos `2`, `10` | `Built` |
| `FR1.5` | Ao final, roda `bob doctor` e exibe o resultado | U1 | U1-T3, U1-T4, U1-T5 | #187, #188, #189 | `src/bob_quality/setup_cmd.py`, `scripts/install.sh` | `tests/test_setup_cmd.py`, `tests/test_install_sh.py`, passo `2` | `Built` |
| `FR1.6` | Oferece prompt de IA passo a passo sem depender de `install.sh` (alternativa) | U8 | U8-T1, U8-T2, U8-T4 | #209, #211, #213 | `docs/instalacao-por-ia.md`, `docs/getting-started/ai-install-prompt.md` | `tests/test_docs_pins.py`, passo `14` | `Built` |
| `FR1.7` | Prompt de IA atinge exatamente o mesmo resultado do comando único | U8 | U8-T1, U8-T4 | #209, #213 | `docs/getting-started/ai-install-prompt.md`, `scripts/verify-install.sh` | `tests/test_docs_pins.py`, `tests/test_verify_install.py`, passo `14` | `Built` |
| `FR1.8` | Prompt manda parar no 1º erro e mostrar saída completa da configuração e verificação | U8 | U8-T1 | #209 | `docs/instalacao-por-ia.md`, `docs/getting-started/ai-install-prompt.md` | `tests/test_docs_pins.py::test_prompt_rules_and_stop_on_error` | `Built` |
| `FR2.1` | Disponibiliza todas as ferramentas que `bob doctor` confere nas versões pinadas | U2, U1, U3 | U2-T1, U1-T3, U3-T2 | #183, #187, #192 | `src/bob_quality/npm_tools.py`, `src/bob_quality/doctor.py`, `src/bob_quality/gitleaks.py` | `tests/test_npm_pin.py`, `tests/test_doctor.py`, passo `2` | `Built` |
| `FR2.2` | Baixa e confere `gitleaks` 8.30.1 em Linux e macOS (`x64` e `arm64`) | U3, U9 | U3-T1, U3-T2, U3-T3, U9-T1 | #191, #192, #193, #216 | `src/bob_quality/gitleaks.py`, `.github/workflows/release.yml` | `tests/test_gitleaks.py`, `tests/test_doctor_install.py`, passo `2`, `E0` (4 runners) | `Built` |
| `FR2.3` | Falha de integridade de binário baixado aborta com exit `4` sem instalar | U3 | U3-T1, U3-T3 | #191, #193 | `src/bob_quality/gitleaks.py`, `scripts/verify-install.sh` | `tests/test_gitleaks.py`, passo `9a` | `Built` |
| `FR2.4` | Não altera dependências do projeto (`package.json`, lockfiles, `requirements`) | U1 | U1-T3, U1-T5 | #187, #189 | `src/bob_quality/setup_cmd.py`, `scripts/verify-install.sh` | `tests/test_setup_cmd.py::test_setup_does_not_touch_the_project_package_files`, passo `8` | `Built` |
| `FR2.5` | `bob doctor` confere as ferramentas isoladas do bob, não o `node_modules` do projeto | U2 | U2-T1 | #183 | `src/bob_quality/npm_tools.py`, `src/bob_quality/doctor.py` | `tests/test_npm_pin.py`, `tests/test_doctor.py` | `Built` |
| `FR3.1` | Instala as 3 skills (`bob-check`, `harden`, `review-report`) no projeto | U1 | U1-T1, U1-T2, U1-T5 | #184, #185, #186, #189 | `src/bob_quality/install_skills.py` | `tests/test_project_skills.py`, `tests/test_package.py`, passo `4` | `Built` |
| `FR3.2` | Skills ficam numa única pasta `.agents/skills` (sem cópia em `.claude`, `.github`, `.cursor`, `.devin`) | U1 | U1-T2, U1-T5 | #185, #186, #189 | `src/bob_quality/install_skills.py` | `tests/test_project_skills.py::test_install_creates_only_agents_skills`, passo `4` | `Built` |
| `FR3.3` | Cada agente carrega cada skill uma única vez; avisa duplicatas em `.claude`/`.github` | U1 | U1-T1, U1-T2, U1-T5 | #184, #185, #186, #189 | `src/bob_quality/install_skills.py`, `pyproject.toml` | `tests/test_project_skills.py::test_copies_in_claude_and_github_skills_are_reported_as_duplicates`, passo `4` | `Built` |
| `FR3.4` | Preserva skills de outras origens e pastas sem marcador `.bob-version` | U1 | U1-T2, U1-T5 | #185, #186, #189 | `src/bob_quality/install_skills.py` | `tests/test_project_skills.py::test_unmarked_folder_is_preserved_and_reported`, passo `8` | `Built` |
| `FR4.1` | Cria `bob.yaml` se o projeto não tiver um | U4 | U4-T1, U4-T2, U4-T3 | #195, #197, #198 | `src/bob_quality/init_config.py`, `src/bob_quality/setup_cmd.py` | `tests/test_init_config.py`, `tests/test_setup_cmd.py`, passo `5` | `Built` |
| `FR4.2` | Usa exatamente os padrões do README exceto `paths.include` (CT7) | U4 | U4-T1, U4-T1c, U4-T3 | #195, #198, #199 | `src/bob_quality/init_config.py` | `tests/test_init_config.py`, passo `5` | `Built` |
| `FR4.3` | Deriva `paths.include` das pastas de código reais do projeto | U4 | U4-T1, U4-T3 | #195, #198 | `src/bob_quality/init_config.py` | `tests/test_init_config.py`, passo `5` (`[src]`, `[app]`) | `Built` |
| `FR4.4` | `bob.yaml` gerado é válido (`bob check` não sai com `4` por config) | U4 | U4-T1, U4-T1b, U4-T3 | #195, #196, #198 | `src/bob_quality/init_config.py`, `src/bob_quality/config.py`, `src/bob_quality/cli.py` | `tests/test_init_config.py`, `tests/test_check_dispatch.py`, passo `5` | `Built` |
| `FR4.5` | Sem pasta de código reconhecível, gera `paths.include: ["."]` válido e emite aviso | U4 | U4-T1, U4-T2, U4-T3 | #195, #197, #198 | `src/bob_quality/init_config.py`, `src/bob_quality/setup_cmd.py` | `tests/test_init_config.py`, `tests/test_setup_cmd.py`, passo `5` | `Built` |
| `FR4.6` | Se `bob.yaml` já existe, preserva byte a byte e avisa o dev | U4 | U4-T1, U4-T2, U4-T3 | #195, #197, #198 | `src/bob_quality/init_config.py`, `src/bob_quality/setup_cmd.py` | `tests/test_init_config.py`, passo `8` | `Built` |
| `FR5.1` | Instala hook `pre-push` ativo que roda `bob check --gates crap,dry,deps` | U5 | U5-T1, U5-T2, U5-T3 | #200, #201, #202 | `src/bob_quality/hook_install.py`, `src/bob_quality/setup_cmd.py` | `tests/test_hook_install.py`, `tests/test_hook.py`, passos `6`, `12` | `Built` |
| `FR5.2` | Hook funciona num `git push` comum com `PATH=/usr/bin:/bin`, sem ativar venv | U5 | U5-T1, U5-T3 | #200, #202 | `src/bob_quality/hook_install.py` | `tests/test_hook.py`, passo `6` | `Built` |
| `FR5.3` | Preserva hook `pre-push` alheio ou `core.hooksPath` customizado e avisa o dev | U5 | U5-T1, U5-T2, U5-T3 | #200, #201, #202 | `src/bob_quality/hook_install.py`, `src/bob_quality/setup_cmd.py` | `tests/test_hook_install.py`, `tests/test_setup_cmd.py`, passo `8` | `Built` |
| `FR6.1` | `bob update` atualiza para a última release publicada (ignora pré-release e rascunho) | U7 | U7-T2, U7-T3 | #206, #208 | `src/bob_quality/update.py`, `src/bob_quality/cli.py` | `tests/test_update.py`, passo `10` | `Built` |
| `FR6.2` | Após `bob update`, `bob doctor` sai `0` e `.agents/skills` ficam na versão nova | U7 | U7-T1, U7-T2, U7-T3 | #203, #206, #208 | `src/bob_quality/update.py`, `src/bob_quality/project_version.py` | `tests/test_update.py`, `tests/test_project_version.py`, passo `10` | `Built` |
| `FR6.3` | `bob update` preserva `bob.yaml`, `.bob/waivers.yaml`, hooks e skills alheias | U7 | U7-T2, U7-T3 | #206, #208 | `src/bob_quality/update.py`, `scripts/verify-install.sh` | `tests/test_update.py`, passo `10` | `Built` |
| `FR6.4` | Exibe a versão instalada no CLI e no projeto (`bob --version` e `bob doctor`) | U7 | U7-T1, U7-T2, U7-T3 | #203, #206, #208 | `src/bob_quality/project_version.py`, `src/bob_quality/doctor.py`, `src/bob_quality/cli.py` | `tests/test_project_version.py`, `tests/test_doctor.py`, passos `2`, `10` | `Built` |
| `FR6.5` | Se já está na última release, `bob update` avisa, não altera nada e sai com `0` | U7 | U7-T2, U7-T3 | #206, #208 | `src/bob_quality/update.py` | `tests/test_update.py::test_up_to_date_prints_and_changes_nothing`, passo `11` | `Built` |
| `FR7.1` | Ao final, mostra resumo do que instalou, preservou, perfil do shell e `bob doctor` | U1, U4, U5, U6 | U1-T3, U4-T2, U5-T2, U6-T2 | #187, #197, #201, #205 | `src/bob_quality/setup_cmd.py`, `src/bob_quality/messages.py` | `tests/test_setup_cmd.py`, passos `2`, `5`, `6`, `8`, `13` | `Built` |
| `FR7.2` | Em falha, indica o passo que falhou e a ação corretiva no `stderr` e sai com `4` | U1, U2, U3, U4, U5, U7 | U1-T3, U1-T4, U2-T1, U3-T1, U4-T2, U5-T2, U7-T2 | #183, #187, #188, #191, #197, #201, #206 | `src/bob_quality/messages.py`, `scripts/install.sh` | `tests/test_messages.py`, `tests/test_install_sh.py`, passo `1` | `Built` |
| `FR7.3` | Confere Python (`>=3.10`) e Node (`>=22.18.0 <23`) antes de instalar | U1 | U1-T3, U1-T4, U1-T5 | #187, #188, #189 | `scripts/install.sh`, `src/bob_quality/setup_cmd.py` | `tests/test_install_sh.py`, `tests/test_setup_cmd.py`, passo `1` | `Built` |
| `FR8.1` | README (`pt-BR` e `en`) e docs de instalação abrem pelo comando único | U8 | U8-T2, U8-T3 | #211, #212 | `README.md`, `README.en.md`, `docs/instalacao.md`, `website/i18n/en/.../installation.md` | `tests/test_docs_pins.py::test_install_docs_start_with_the_one_liner` | `Built` |
| `FR8.2` | Docs listam requisitos reais (Python e Node) e versões pinadas exatas | U8 | U8-T2, U8-T3 | #211, #212 | `README.md`, `README.en.md`, `docs/**`, `website/**` | `tests/test_docs_pins.py::test_docs_cite_only_the_pinned_versions` | `Built` |
| `FR8.3` | Docs explicam como atualizar (`bob update`) e ver versão (`bob --version`) | U8 | U8-T2 | #211 | `README.md`, `README.en.md`, `docs/instalacao.md`, `website/i18n/en/.../installation.md` | `tests/test_docs_pins.py::test_update_section_shows_update_and_version` | `Built` |
| `FR8.4` | Docs mostram comando único como principal e Prompt de IA como alternativa abaixo | U8 | U8-T2 | #211 | `README.md`, `README.en.md`, `docs/instalacao.md`, `website/i18n/en/.../installation.md` | `tests/test_docs_pins.py::test_alternative_comes_after_the_one_liner_once` | `Built` |
| `FR8.5` | Prompt de IA versionado nos docs em `pt-BR` e `en` na mesma versão do código | U8 | U8-T1, U8-T2 | #209, #211 | `docs/instalacao-por-ia.md`, `docs/getting-started/ai-install-prompt.md`, `website/sidebars.js` | `tests/test_docs_pins.py`, passo `14` | `Built` |

---

## 3. Matriz por História de Usuário (`US1.1` a `US7.2`)

| Story ID | Título | Unit(s) | PR(s) | Evidência de Verificação | Status |
|---|---|---|---|---|---|
| `US1.1` | Instalar e configurar o bob no projeto com um único comando | U1, U6, U9 | #187, #188, #189, #204, #205, #207, #210, #216 | `verify-install.sh` passos `2` e `13`; `tests/test_install_sh.py` | `Built` |
| `US1.2` | Parar cedo com mensagem clara quando falta pré-requisito | U1 | #187, #188, #189 | `verify-install.sh` passo `1`; `tests/test_install_sh.py`, `tests/test_setup_cmd.py` | `Built` |
| `US1.3` | Baixar e conferir `gitleaks` 8.30.1 por SHA-256 sem pré-requisito manual | U3 | #191, #192, #193, #194 | `verify-install.sh` passos `2` e `9a`; `tests/test_gitleaks.py` | `Built` |
| `US1.4` | Rodar `bob doctor` isolado do `node_modules` do projeto e com fonte única npm | U2 | #183 | `tests/test_npm_pin.py`, `tests/test_doctor.py` | `Built` |
| `US1.5` | Instalar via Prompt de IA sem depender de `install.sh` | U8 | #209, #211, #213 | `verify-install.sh` passo `14`; `tests/test_docs_pins.py` | `Built` |
| `US2.1` | Ter as 3 skills em `.agents/skills` sem plugin nativo nem duplicatas | U1 | #184, #185, #186, #189 | `verify-install.sh` passo `4`; `tests/test_project_skills.py`, `tests/test_package.py` | `Built` |
| `US3.1` | Gerar `bob.yaml` inicial válido com `paths.include` derivado do projeto | U4 | #195, #196, #197, #198, #199 | `verify-install.sh` passo `5`; `tests/test_init_config.py` | `Built` |
| `US3.2` | Preservar `bob.yaml`, waivers, hook e skills existentes sem sobrescrever | U4, U5 | #195, #197, #198, #200, #201, #202 | `verify-install.sh` passos `7` e `8`; `tests/test_init_config.py`, `tests/test_hook_install.py` | `Built` |
| `US4.1` | Ter hook `pre-push` ativo e rápido (`< 60 s`) num `git push` comum | U5 | #200, #201, #202 | `verify-install.sh` passos `6` e `12`; `tests/test_hook_install.py`, `tests/test_hook.py` | `Built` |
| `US5.1` | Atualizar o bob no projeto com `bob update` preservando configurações | U7 | #203, #206, #208 | `verify-install.sh` passos `10` e `11`; `tests/test_update.py` | `Built` |
| `US5.2` | Consultar a versão instalada do bob e das skills do projeto | U7 | #203, #206, #208 | `verify-install.sh` passos `2` e `10`; `tests/test_project_version.py` | `Built` |
| `US6.1` | Ver resumo final claro e erros acionáveis em `en` e `pt-BR` | U1, U4, U5, U6, U7 | #187, #188, #197, #201, #205, #206 | `tests/test_messages.py`, `tests/test_setup_cmd.py`, `verify-install.sh` | `Built` |
| `US7.1` | Ler documentação atualizada com comando único, atualização e Prompt de IA | U8, U9 | #209, #211, #212, #213, #214, #215 | `tests/test_docs_pins.py`, `tests/test_release_checks.py`, `website / build` | `Built` |
| `US7.2` | Publicar release `v0.1.0` verificada em 4 plataformas sem promover pré-release a `latest` | U7, U9, 3.6 | #206, #208, #214, #215, #216, #217, #221 | `verify-install.sh` passo `10`, `tests/test_release_workflow.py`, `E0` (`release.yml` `dry_run: true`) | `Built` |

---

## 4. Inventário Completo de Unidades e Tarefas (`U1..U9` + `3.6`)

| Unit / Estágio | Tarefa | Branch | PR(s) | Status | Rodadas de correção |
|---|---|---|---|---|---:|
| `U2` (`u2-doctor-fonte-unica`) | `T1` Fonte única de versões npm e isolamento do `bob doctor` | `aidlc/u2-doctor-fonte-unica/t1-npm-single-source` | [#183](https://github.com/fazedordecodigo/bob/pull/183) | `merged` | 0 |
| `U1` (`u1-walking-skeleton`) | `T1` Levar skills, manifesto e LICENSE no wheel | `aidlc/u1-walking-skeleton/t1-wheel-plugin` | [#184](https://github.com/fazedordecodigo/bob/pull/184) | `merged` | 0 |
| `U1` (`u1-walking-skeleton`) | `T2` Instalar as skills do projeto em `.agents/skills` com posse | `aidlc/u1-walking-skeleton/t2-project-skills` | [#185](https://github.com/fazedordecodigo/bob/pull/185), [#186](https://github.com/fazedordecodigo/bob/pull/186) | `merged` | 0 |
| `U1` (`u1-walking-skeleton`) | `T3` `bob setup` e pastas do usuário | `aidlc/u1-walking-skeleton/t3-bob-setup` | [#187](https://github.com/fazedordecodigo/bob/pull/187) | `merged` | 0 |
| `U1` (`u1-walking-skeleton`) | `T4` Comando único `scripts/install.sh` | `aidlc/u1-walking-skeleton/t4-install-sh` | [#188](https://github.com/fazedordecodigo/bob/pull/188) | `merged` | 0 |
| `U1` (`u1-walking-skeleton`) | `T5` Harness `scripts/verify-install.sh` (passos 1–4, 7–8, 9b) | `aidlc/u1-walking-skeleton/t5-verify-install` | [#189](https://github.com/fazedordecodigo/bob/pull/189) | `merged` | 0 |
| `U1` (`u1-walking-skeleton`) | `T6` Workflow `.github/workflows/verify-install.yml` | `aidlc/u1-walking-skeleton/t6-verify-install-ci` | [#190](https://github.com/fazedordecodigo/bob/pull/190) | `merged` | 0 |
| `U3` (`u3-gitleaks`) | `T1` Módulo `src/bob_quality/gitleaks.py` e chaves de idioma | `aidlc/u3-gitleaks/t1-gitleaks-installer` | [#191](https://github.com/fazedordecodigo/bob/pull/191) | `merged` | 0 |
| `U3` (`u3-gitleaks`) | `T2` Integrar `gitleaks` em `bob setup` e `bob doctor` | `aidlc/u3-gitleaks/t2-setup-doctor-gitleaks` | [#192](https://github.com/fazedordecodigo/bob/pull/192) | `merged` | 0 |
| `U3` (`u3-gitleaks`) | `T3` Harness `verify-install.sh` sem fixture de `gitleaks` e passo `9a` | `aidlc/u3-gitleaks/t3-verify-install-gitleaks` | [#193](https://github.com/fazedordecodigo/bob/pull/193) | `merged` | 0 |
| `U3` (`u3-gitleaks`) | `T4` Documentação de `gitleaks` gerenciado e ADRs 0008–0019 | `aidlc/u3-gitleaks/t4-docs-adr` | [#194](https://github.com/fazedordecodigo/bob/pull/194) | `merged` | 0 |
| `U4` (`u4-bob-yaml`) | `T1` Gerador `src/bob_quality/init_config.py` (CT7) | `aidlc/u4-bob-yaml/t1-init-config` | [#195](https://github.com/fazedordecodigo/bob/pull/195) | `merged` | 0 |
| `U4` (`u4-bob-yaml`) | `T1b` Aceitar `bob.yaml` sem `languages` no `bob check` | `aidlc/u4-bob-yaml/t1b-empty-languages` | [#196](https://github.com/fazedordecodigo/bob/pull/196) | `merged` | 0 |
| `U4` (`u4-bob-yaml`) | `T2` Passo `bob.yaml` no `bob setup` | `aidlc/u4-bob-yaml/t2-setup-bob-yaml` | [#197](https://github.com/fazedordecodigo/bob/pull/197) | `merged` | 0 |
| `U4` (`u4-bob-yaml`) | `T3` Passo `5` e expansão dos passos `7` e `8` no harness | `aidlc/u4-bob-yaml/t3-verify-install-bob-yaml` | [#198](https://github.com/fazedordecodigo/bob/pull/198) | `merged` | 0 |
| `U4` (`u4-bob-yaml`) | `T1c` Alinhar README e docs ao template CT7 | `aidlc/u4-bob-yaml/t1c-docs-bob-yaml` | [#199](https://github.com/fazedordecodigo/bob/pull/199) | `merged` | 0 |
| `U5` (`u5-hook-pre-push`) | `T1` Instalador `src/bob_quality/hook_install.py` (CT10) e guarda hermética | `aidlc/u5-hook-pre-push/t1-hook-installer` | [#200](https://github.com/fazedordecodigo/bob/pull/200) | `merged` | 0 |
| `U5` (`u5-hook-pre-push`) | `T2` Passo `hook` no `bob setup` | `aidlc/u5-hook-pre-push/t2-setup-hook` | [#201](https://github.com/fazedordecodigo/bob/pull/201) | `merged` | 0 |
| `U5` (`u5-hook-pre-push`) | `T3` Passos `6` e `12` no harness `scripts/verify-install.sh` | `aidlc/u5-hook-pre-push/t3-verify-install-hook` | [#202](https://github.com/fazedordecodigo/bob/pull/202) | `merged` | 0 |
| `U6` (`u6-perfil-shell`) | `T1` Passo `perfil` em `scripts/install.sh` (CT16) | `aidlc/u6-perfil-shell/t1-install-sh-profile` | [#204](https://github.com/fazedordecodigo/bob/pull/204) | `merged` | 0 |
| `U6` (`u6-perfil-shell`) | `T2` Linha `perfil do shell:` no resumo do `bob setup` | `aidlc/u6-perfil-shell/t2-setup-profile-line` | [#205](https://github.com/fazedordecodigo/bob/pull/205) | `merged` | 0 |
| `U6` (`u6-perfil-shell`) | `T3` Passo `13` no harness `scripts/verify-install.sh` | `aidlc/u6-perfil-shell/t3-verify-install-profile` | [#207](https://github.com/fazedordecodigo/bob/pull/207) | `merged` | 0 |
| `U6` (`u6-perfil-shell`) | `T4` Cobertura de `BOB_SHELL_PROFILE` fora do `HOME` | `aidlc/u6-perfil-shell/t4-profile-outside-home` | [#210](https://github.com/fazedordecodigo/bob/pull/210) | `merged` | 0 |
| `U7` (`u7-update-versao`) | `T1` `src/bob_quality/project_version.py` e linha `project skills:` no `bob doctor` | `aidlc/u7-update-versao/t1-project-version` | [#203](https://github.com/fazedordecodigo/bob/pull/203) | `merged` | 0 |
| `U7` (`u7-update-versao`) | `T2` Subcomando `bob update` (`src/bob_quality/update.py`) e `bob --version` | `aidlc/u7-update-versao/t2-bob-update` | [#206](https://github.com/fazedordecodigo/bob/pull/206) | `merged` | 0 |
| `U7` (`u7-update-versao`) | `T3` Passos `10` e `11` no harness `scripts/verify-install.sh` | `aidlc/u7-update-versao/t3-verify-install-update` | [#208](https://github.com/fazedordecodigo/bob/pull/208) | `merged` | 0 |
| `U8` (`u8-docs`) | `T1` Prompt de IA (`docs/instalacao-por-ia.md` e `ai-install-prompt.md`) + `tests/test_docs_pins.py` | `aidlc/u8-docs/t1-ai-install-prompt` | [#209](https://github.com/fazedordecodigo/bob/pull/209) | `merged` | 0 |
| `U8` (`u8-docs`) | `T2` Reescrever `README.md`, `README.en.md` e páginas de instalação | `aidlc/u8-docs/t2-install-docs` | [#211](https://github.com/fazedordecodigo/bob/pull/211) | `merged` | 0 |
| `U8` (`u8-docs`) | `T3` Atualizar páginas de agentes e hooks (`pt-BR` e `en`) | `aidlc/u8-docs/t3-agent-hook-docs` | [#212](https://github.com/fazedordecodigo/bob/pull/212) | `merged` | 0 |
| `U8` (`u8-docs`) | `T4` Passo `14` (paridade A vs. B do Prompt de IA) em `scripts/verify-install.sh` | `aidlc/u8-docs/t4-verify-install-parity` | [#213](https://github.com/fazedordecodigo/bob/pull/213) | `merged` | 0 |
| `U9` (`u9-release-v0-1-0`) | `T1` Workflow `.github/workflows/release.yml` e modo `VERIFY_DIST` no harness | `aidlc/u9-release-v0-1-0/t1-release-workflow` | [#216](https://github.com/fazedordecodigo/bob/pull/216) | `merged` | 0 |
| `U9` (`u9-release-v0-1-0`) | `T2` Runbook operacional `docs/release-checks.md` (`E0..E6`) em `pt-BR` e `en` | `aidlc/u9-release-v0-1-0/t2-release-checks-docs` | [#214](https://github.com/fazedordecodigo/bob/pull/214) | `merged` | 0 |
| `U9` (`u9-release-v0-1-0`) | `T3` Publicação dos ADRs `0020` a `0029` no site Docusaurus | `aidlc/u9-release-v0-1-0/t3-publish-adrs` | [#215](https://github.com/fazedordecodigo/bob/pull/215) | `merged` | 0 |
| `3.6` (`build-and-test`) | `T1` Guarda hermética completa em `tests/test_hermetic.py` (`U4-N14`) | `aidlc/build-and-test/t1-hermetic-u4-n14` | [#217](https://github.com/fazedordecodigo/bob/pull/217) | `merged` | 0 |
| `3.6` (`build-and-test`) | `T2` Portabilidade macOS (`darwin-arm64`/`darwin-x64`) para o ensaio `E0` | `aidlc/build-and-test/t2-macos-portability` | [#221](https://github.com/fazedordecodigo/bob/pull/221) | `merged` | 0 |
