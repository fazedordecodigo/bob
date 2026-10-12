"""Catálogo i18n. A mensagem viaja como dado e vira texto só na saída."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

Language = Literal["en", "pt-BR"]
LANGUAGES: tuple[Language, ...] = ("en", "pt-BR")
DEFAULT_LANGUAGE: Language = "en"


@dataclass(frozen=True)
class Message:
    key: str
    params: tuple[tuple[str, object], ...] = ()


Text = Union[Message, str]


def msg(key: str, /, **params: object) -> Message:
    return Message(key, tuple(params.items()))


def render(text: Text, lang: Language) -> str:
    """Texto cru (saída de ferramenta) passa como veio; Message usa o catálogo."""
    if isinstance(text, str):
        return text
    values = {name: _rendered(value, lang) for name, value in text.params}
    return CATALOG[lang][text.key].format(**values)


def _rendered(value: object, lang: Language) -> object:
    if isinstance(value, Message):
        return render(value, lang)
    return value


def t(lang: Language, key: str, /, **params: object) -> str:
    return render(msg(key, **params), lang)


def reason(exc: BaseException) -> Text:
    if exc.args and isinstance(exc.args[0], Message):
        return exc.args[0]
    return str(exc)


_EN: dict[str, str] = {
    "cli.description": "Quality gates for agents.",
    "cli.lang": "Output language: en or pt-BR (default: en)",
    "cli.check": "Run the requested gates and write .bob/",
    "cli.gates": "Comma-separated list (default: crap,dry,deps)",
    "cli.crap": "Measure CRAP of the changed functions",
    "cli.dry": "Report new clones in the diff, without blocking",
    "cli.deps": "Check dependency cycles and rules",
    "cli.mutate": "Mutate the changed functions with mutmut",
    "cli.since_last_run": "Reuse the cache; already the default behavior",
    "cli.waive": "Record a waiver with a one-line reason",
    "cli.waive_target": "mutant id or function name",
    "cli.doctor": "Check the pinned tools and the installed versions",
    "cli.install": "Install the npm tools with npm ci in the package (or in a user cache)",
    "config.not_found": "config file not found: {path}",
    "config.not_mapping": "bob.yaml must be a mapping",
    "config.invalid_language": "invalid language: {value} (use en or pt-BR)",
    "config.invalid_yaml": "invalid YAML in {path}: {detail}",
    "config.key_mapping": "{path}: {key} must be a mapping",
    "config.key_number": "{path}: {key} must be a number",
    "config.key_string": "{path}: {key} must be a string",
    "config.key_string_list": "{path}: {key} must be a list of strings",
    "config.key_integer": "{path}: {key} must be an integer",
    "config.key_finite": "{path}: {key} must be finite",
    "config.key_greater_than": "{path}: {key} must be greater than {bound}",
    "config.key_at_least": "{path}: {key} must be at least {bound}",
    "config.key_one_of": "{path}: {key} must be {left} or {right}",
    "file.unknown_key": "{path}: unknown key {key}",
    "check.gate_not_implemented": "gate not implemented in this slice",
    "tool.missing": "missing tool: {tool}",
    "tool.detail": "{tool}: {detail}",
    "git.ls_files_failed": "git ls-files failed: {detail}",
    "suite.pyproject_unreadable": "unreadable pyproject.toml: {detail}",
    "suite.setup_cfg_unreadable": "unreadable setup.cfg: {detail}",
    "probe.baseline_failed": "baseline tests failed before measuring",
    "probe.c8_no_report": "c8 did not write coverage-final.json",
    "probe.typescript_skipped": "TypeScript skipped: {reason}",
    "probe.joined": "{first}; {second}",
    "npm.node_missing": "Node missing: install Node.js to measure TypeScript (c8 and vitest via npx)",
    "npm.manifest_missing": (
        "plugin package.json (bob-quality-tools) not found; c8 and vitest are pinned in it"
    ),
    "npm.deps_missing": "plugin npm dependencies missing: {hint}",
    "npm.cache_fallback": "{command} failed with {code}; installing in the user cache {cache}",
    "npm.cache_unavailable": "could not prepare the user cache {cache}: {detail}",
    "npm.unreadable_version": "unreadable {package} version",
    "npm.c8_failed": "c8/vitest failed",
    "dry.node_missing": "Node missing: install Node.js to run jscpd",
    "dry.deps_missing": (
        "plugin npm dependencies missing: bob doctor --install (#19; jscpd pinned in package.json)"
    ),
    "dry.clone": "{count} new clone in the diff",
    "dry.clones": "{count} new clones in the diff",
    "dry.include_missing": "jscpd: include path missing: {paths}",
    "dry.no_report": "jscpd did not write the JSON",
    "deps.node_missing": (
        "Node missing: install Node.js for the dependency gate (dependency-cruiser via npx)"
    ),
    "deps.grimp_failed": "grimp could not build the graph: {detail}",
    "deps.grimp_unreadable": "grimp returned an unreadable graph",
    "deps.contract_broken": "broken contract: {name}",
    "deps.tool_failed": "dependency tool failed",
    "deps.cycle_rule": "Forbidden dependency cycle",
    "deps.unnamed": "dependency",
    "deps.cruiser_no_list": "dependency-cruiser: JSON without a violations list",
    "deps.linter_not_empty": "import-linter: output is not an empty report",
    "mutate.cache_invalid": "invalid mutation cache: {detail}",
    "mutate.unwaived": "survivor without waiver: {mutants}",
    "mutate.uncovered_one": "{count} mutant without a test",
    "mutate.uncovered_many": "{count} mutants without a test",
    "mutmut.baseline_timeout": "baseline pytest timed out",
    "mutmut.unreadable_version": "unreadable mutmut version: {raw}",
    "mutmut.timeout": "mutmut timed out",
    "mutmut.unknown_status": "unknown mutmut status: {label!r}",
    "stryker.unknown_status": "unknown Stryker status: {label!r}",
    "stryker.bad_report": "invalid Stryker report: {detail}",
    "stryker.no_report": "Stryker did not write the report",
    "mutmut.bad_id": "mutant id outside the contract: {mutant_id}",
    "mutmut.suite_fails_in_mutants": (
        "the suite passes in the repository and fails inside mutants/;"
        " check also_copy and the [mutmut] configuration: {detail}"
    ),
    "waiver.no_reason": "waiver without a reason: pass --reason with one line",
    "waiver.invalid_yaml": "invalid YAML in {path}: {detail}",
    "waiver.file_not_mapping": "{path} must be a mapping",
    "waiver.list_required": "{path}: {field} must be a list",
    "waiver.entry_mapping": "{path}: {field} must be a mapping",
    "waiver.field_string": "{path}: {field} must be a string",
    "waiver.reason_line": "{path}: {field} must be one non-empty line",
    "waiver.no_target": "waiver without a target",
    "coverage.invalid_json": "invalid coverage.json",
    "coverage.no_files": "coverage.json without a files key",
    "coverage.invalid_entry": "invalid entry for {path}",
    "istanbul.invalid_json": "invalid coverage-final.json",
    "istanbul.not_object": "coverage-final.json must be an object of files",
    "istanbul.invalid_entry": "invalid istanbul entry for {path}",
    "istanbul.invalid_map": "invalid statement map `s`",
    "istanbul.invalid_statement": "invalid statement: {key}",
    "jscpd.invalid_json": "jscpd: invalid JSON",
    "jscpd.no_duplicates": "jscpd: JSON without the duplicates list",
    "jscpd.malformed": "jscpd: malformed duplicate",
    "jscpd.no_size": "jscpd: duplicate without lines or tokens",
    "jscpd.invalid_similarity": "jscpd: invalid similarity",
    "jscpd.missing_side": "jscpd: duplicate without {key}",
    "jscpd.side_no_name": "jscpd: {key} without name",
    "jscpd.side_no_lines": "jscpd: {key} without lines",
    "lizard.unexpected_row": "unexpected CSV row: {row!r}",
    "lizard.invalid_row": "invalid CSV row: {row!r}",
    "doctor.version": "{name} expected {expected} found {found}",
    "doctor.missing": "missing",
    "doctor.install_node": "Install Node.js {version} ({url})",
    "status.passed": "passed",
    "status.warn": "warning",
    "status.failed": "failed",
    "status.not_run": "not run",
    "report.title": "# bob report",
    "report.date": "- Date: {value}",
    "report.tools": "- Tools: {value}",
    "report.verdict": "## Verdict",
    "report.gate": "- {mark} `{name}`: {status}",
    "report.gate_reason": "- {mark} `{name}`: {status} ({reason})",
    "report.focus": "## Where to focus the review",
    "report.no_focus": "- No changed file with CRAP risk.",
    "report.focus_item": "- `{file}` (risk {risk})",
    "report.focus_item_clone": "- `{file}` (risk {risk}, clone)",
    "report.top_crap": "## Top 5 functions by CRAP (diff)",
    "report.no_top_crap": "No changed function measured.",
    "report.crap_header": "| Function | File | CC | Coverage | CRAP | Delta |",
    "report.old_debt": "## Information (old debt)",
    "report.old_debt_item": "- `{name}` at `{loc}` CRAP {crap} (outside the diff; does not block)",
    "report.survivors": "## Surviving mutants",
    "report.no_survivors": "No surviving mutants.",
    "report.survivor_header": "| Id | Function | Location | Operator | Waiver |",
    "report.no_coverage": "## Mutants without tests",
    "report.no_uncovered": "No mutants without tests.",
    "report.uncovered_total": "⚠️ Total: {total}. Does not block.",
    "report.uncovered_header": "| Function | File | Mutants |",
    "report.no_waivers": "No waivers.",
    "report.waiver_header": "| Target | Reason | Author | Date |",
    "report.dependencies": "## Dependency violations and cycles",
    "report.dependency_edge": "- `{origin} → {destination}` ({rule})",
    "report.deps_not_run": "- Gate not run.",
    "report.deps_failed": "- {reason}",
    "report.no_violations": "- No dependency violations.",
    "report.old_dependencies": "## Information (dependencies outside the diff)",
    "report.old_dependency_item": "{item} (outside the diff; does not block)",
    "report.clones": "## New clones",
    "report.no_clones": "No new clones in the diff.",
    "report.clones_not_run_reason": "Not run ({reason}).",
    "report.clones_not_run": "Not run.",
    "report.clone_item": (
        "- {left} ↔ {right} — {lines} lines, {tokens} tokens, similarity {similarity}"
    ),
    "report.exact": "exact",
    "report.reproduce": "## How to reproduce",
    "action.truncated": "\n\n_…report truncated to fit in the GitHub comment._\n",
    "action.required": "repo, pr, and token are required",
    "action.report_missing": "`{path}` was not generated.",
    "action.comments_invalid": "invalid comment list",
}

_PT_BR: dict[str, str] = {
    "cli.description": "Gates de qualidade para agentes.",
    "cli.lang": "Idioma da saída: en ou pt-BR (padrão: en)",
    "cli.check": "Roda os gates pedidos e grava .bob/",
    "cli.gates": "Lista separada por vírgula (padrão: crap,dry,deps)",
    "cli.crap": "Mede CRAP das funções alteradas",
    "cli.dry": "Reporta clones novos no diff, sem bloquear",
    "cli.deps": "Verifica ciclos e regras de dependência",
    "cli.mutate": "Muta funções alteradas com mutmut",
    "cli.since_last_run": "Reusa o cache; já é o comportamento padrão",
    "cli.waive": "Registra um waiver com motivo de uma linha",
    "cli.waive_target": "id do mutante ou nome da função",
    "cli.doctor": "Verifica as ferramentas pinadas e as versões instaladas",
    "cli.install": "Instala as ferramentas npm com npm ci no pacote (ou num cache do usuário)",
    "config.not_found": "arquivo de configuração não encontrado: {path}",
    "config.not_mapping": "bob.yaml deve ser um mapeamento",
    "config.invalid_language": "idioma inválido: {value} (use en ou pt-BR)",
    "config.invalid_yaml": "YAML inválido em {path}: {detail}",
    "config.key_mapping": "{path}: {key} deve ser um mapeamento",
    "config.key_number": "{path}: {key} deve ser um número",
    "config.key_string": "{path}: {key} deve ser um texto",
    "config.key_string_list": "{path}: {key} deve ser uma lista de textos",
    "config.key_integer": "{path}: {key} deve ser um inteiro",
    "config.key_finite": "{path}: {key} deve ser finito",
    "config.key_greater_than": "{path}: {key} deve ser maior que {bound}",
    "config.key_at_least": "{path}: {key} deve ser no mínimo {bound}",
    "config.key_one_of": "{path}: {key} deve ser {left} ou {right}",
    "file.unknown_key": "{path}: chave desconhecida {key}",
    "check.gate_not_implemented": "gate não implementado nesta fatia",
    "tool.missing": "ferramenta ausente: {tool}",
    "tool.detail": "{tool}: {detail}",
    "git.ls_files_failed": "git ls-files falhou: {detail}",
    "suite.pyproject_unreadable": "pyproject.toml ilegível: {detail}",
    "suite.setup_cfg_unreadable": "setup.cfg ilegível: {detail}",
    "probe.baseline_failed": "testes da baseline falharam antes de medir",
    "probe.c8_no_report": "c8 não gravou coverage-final.json",
    "probe.typescript_skipped": "TypeScript pulado: {reason}",
    "probe.joined": "{first}; {second}",
    "npm.node_missing": "Node ausente: instale Node.js para medir TypeScript (c8 e vitest via npx)",
    "npm.manifest_missing": (
        "package.json do plugin (bob-quality-tools) não encontrado; c8 e vitest ficam fixados nele"
    ),
    "npm.deps_missing": "dependências npm do plugin ausentes: {hint}",
    "npm.cache_fallback": "{command} falhou com {code}; instalando no cache do usuário {cache}",
    "npm.cache_unavailable": "não foi possível preparar o cache do usuário {cache}: {detail}",
    "npm.unreadable_version": "versão de {package} ilegível",
    "npm.c8_failed": "c8/vitest falhou",
    "dry.node_missing": "Node ausente: instale Node.js para rodar o jscpd",
    "dry.deps_missing": (
        "dependências npm do plugin ausentes: bob doctor --install "
        "(#19; jscpd fixado no package.json)"
    ),
    "dry.clone": "{count} clone novo no diff",
    "dry.clones": "{count} clones novos no diff",
    "dry.include_missing": "jscpd: caminho de include ausente: {paths}",
    "dry.no_report": "jscpd não gravou o JSON",
    "deps.node_missing": (
        "Node ausente: instale Node.js para o gate de dependências (dependency-cruiser via npx)"
    ),
    "deps.grimp_failed": "grimp não montou o grafo: {detail}",
    "deps.grimp_unreadable": "grimp devolveu um grafo ilegível",
    "deps.contract_broken": "contrato quebrado: {name}",
    "deps.tool_failed": "ferramenta de dependência falhou",
    "deps.cycle_rule": "Proibido ciclo de dependência",
    "deps.unnamed": "dependência",
    "deps.cruiser_no_list": "dependency-cruiser: JSON sem a lista violations",
    "deps.linter_not_empty": "import-linter: saída não é um relatório vazio",
    "mutate.cache_invalid": "cache de mutação inválido: {detail}",
    "mutate.unwaived": "sobrevivente sem waiver: {mutants}",
    "mutate.uncovered_one": "{count} mutante sem teste",
    "mutate.uncovered_many": "{count} mutantes sem teste",
    "mutmut.baseline_timeout": "pytest da baseline excedeu o tempo limite",
    "mutmut.unreadable_version": "versão do mutmut ilegível: {raw}",
    "mutmut.timeout": "mutmut excedeu o tempo limite",
    "mutmut.unknown_status": "status desconhecido do mutmut: {label!r}",
    "stryker.unknown_status": "status desconhecido do Stryker: {label!r}",
    "stryker.bad_report": "relatório do Stryker inválido: {detail}",
    "stryker.no_report": "o Stryker não gravou o relatório",
    "mutmut.bad_id": "id de mutante fora do contrato: {mutant_id}",
    "mutmut.suite_fails_in_mutants": (
        "a suíte passa no repositório e falha dentro de mutants/;"
        " confira also_copy e a configuração [mutmut]: {detail}"
    ),
    "waiver.no_reason": "waiver sem motivo: informe --reason com uma linha",
    "waiver.invalid_yaml": "YAML inválido em {path}: {detail}",
    "waiver.file_not_mapping": "{path} deve ser um mapeamento",
    "waiver.list_required": "{path}: {field} deve ser uma lista",
    "waiver.entry_mapping": "{path}: {field} deve ser um mapeamento",
    "waiver.field_string": "{path}: {field} deve ser um texto",
    "waiver.reason_line": "{path}: {field} deve ser uma linha não vazia",
    "waiver.no_target": "waiver sem alvo",
    "coverage.invalid_json": "coverage.json inválido",
    "coverage.no_files": "coverage.json sem chave files",
    "coverage.invalid_entry": "entrada inválida para {path}",
    "istanbul.invalid_json": "coverage-final.json inválido",
    "istanbul.not_object": "coverage-final.json deve ser um objeto de arquivos",
    "istanbul.invalid_entry": "entrada istanbul inválida para {path}",
    "istanbul.invalid_map": "mapa de statements `s` inválido",
    "istanbul.invalid_statement": "statement inválido: {key}",
    "jscpd.invalid_json": "jscpd: JSON inválido",
    "jscpd.no_duplicates": "jscpd: JSON sem a lista duplicates",
    "jscpd.malformed": "jscpd: duplicata fora do formato",
    "jscpd.no_size": "jscpd: duplicata sem lines ou tokens",
    "jscpd.invalid_similarity": "jscpd: similarity inválida",
    "jscpd.missing_side": "jscpd: duplicata sem {key}",
    "jscpd.side_no_name": "jscpd: {key} sem name",
    "jscpd.side_no_lines": "jscpd: {key} sem linhas",
    "lizard.unexpected_row": "linha CSV inesperada: {row!r}",
    "lizard.invalid_row": "linha CSV inválida: {row!r}",
    "doctor.version": "{name} esperada {expected} encontrada {found}",
    "doctor.missing": "ausente",
    "doctor.install_node": "Instale Node.js {version} ({url})",
    "status.passed": "passou",
    "status.warn": "aviso",
    "status.failed": "falhou",
    "status.not_run": "não executado",
    "report.title": "# Relatório bob",
    "report.date": "- Data: {value}",
    "report.tools": "- Ferramentas: {value}",
    "report.verdict": "## Veredito",
    "report.gate": "- {mark} `{name}`: {status}",
    "report.gate_reason": "- {mark} `{name}`: {status} ({reason})",
    "report.focus": "## Onde focar o review",
    "report.no_focus": "- Nenhum arquivo alterado com risco de CRAP.",
    "report.focus_item": "- `{file}` (risco {risk})",
    "report.focus_item_clone": "- `{file}` (risco {risk}, clone)",
    "report.top_crap": "## Top 5 funções por CRAP (diff)",
    "report.no_top_crap": "Nenhuma função alterada medida.",
    "report.crap_header": "| Função | Arquivo | CC | Cobertura | CRAP | Delta |",
    "report.old_debt": "## Informação (dívida antiga)",
    "report.old_debt_item": "- `{name}` em `{loc}` CRAP {crap} (fora do diff; não bloqueia)",
    "report.survivors": "## Mutantes sobreviventes",
    "report.no_survivors": "Nenhum mutante sobrevivente.",
    "report.survivor_header": "| Id | Função | Local | Operador | Waiver |",
    "report.no_coverage": "## Mutantes sem teste",
    "report.no_uncovered": "Nenhum mutante sem teste.",
    "report.uncovered_total": "⚠️ Total: {total}. Não bloqueia.",
    "report.uncovered_header": "| Função | Arquivo | Mutantes |",
    "report.no_waivers": "Nenhum waiver.",
    "report.waiver_header": "| Alvo | Motivo | Autor | Data |",
    "report.dependencies": "## Violações e ciclos de dependência",
    "report.dependency_edge": "- `{origin} → {destination}` ({rule})",
    "report.deps_not_run": "- Gate não executado.",
    "report.deps_failed": "- {reason}",
    "report.no_violations": "- Nenhuma violação de dependência.",
    "report.old_dependencies": "## Informação (dependências fora do diff)",
    "report.old_dependency_item": "{item} (fora do diff; não bloqueia)",
    "report.clones": "## Clones novos",
    "report.no_clones": "Nenhum clone novo no diff.",
    "report.clones_not_run_reason": "Não executado ({reason}).",
    "report.clones_not_run": "Não executado.",
    "report.clone_item": (
        "- {left} ↔ {right} — {lines} linhas, {tokens} tokens, similaridade {similarity}"
    ),
    "report.exact": "exata",
    "report.reproduce": "## Como reproduzir",
    "action.truncated": "\n\n_…relatório truncado para caber no comentário do GitHub._\n",
    "action.required": "repo, pr e token são obrigatórios",
    "action.report_missing": "`{path}` não foi gerado.",
    "action.comments_invalid": "lista de comentários inválida",
}

CATALOG: dict[Language, dict[str, str]] = {"en": _EN, "pt-BR": _PT_BR}
