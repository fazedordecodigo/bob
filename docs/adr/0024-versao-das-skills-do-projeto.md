# Versão das skills do projeto: módulo `project_version`

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

- Módulo novo `src/bob_quality/project_version.py` (parte de C10). Lê `<projeto>/.agents/skills/<nome>/.bob-version` só para os nomes do manifesto empacotado.
- Função pública nova `install_skills.manifest_skill_names(source=None) -> tuple[str, ...]`. É um acréscimo compatível ao CT4.
- Um arquivo vale só se é regular (não symlink) e o conteúdo casa exatamente `\d+\.\d+\.\d+\n`. Erro de leitura, symlink ou conteúdo fora disso contam como ausente.
- Estados: `installed` (todas as skills com a mesma versão); `not_installed` (nenhuma válida, manifesto ilegível ou lista vazia); `mixed` (versões diferentes, ordenadas como tupla numérica, sem repetição). Uma parte ausente e outra válida também é `mixed`, com o marcador `missing` (recomendação A da Q1 da U7).
- O `bob doctor` acrescenta a linha `project skills:` no fim da saída normal, dentro de `_report_pins`, com o `cwd`. Ela não muda o código de saída. Sai só quando os pins foram lidos (no erro do `package.json` continua 0 linhas no stdout).
- O módulo fica separado de `update.py` para evitar o ciclo `doctor → update → setup_cmd → doctor`.

## Consequências

O `bob --version` e o doctor usam a mesma linha (CT8 = CT11). Q1 pendente: se a resposta não for A, só os textos de `mixed` mudam (ET v2 da U7 T1).
