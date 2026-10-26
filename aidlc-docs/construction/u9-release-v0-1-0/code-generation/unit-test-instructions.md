# U9 — Unit Test Instructions

Rodar na raiz do repo, na branch da ET.

```sh
python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]'
/tmp/dev/bin/pytest tests/test_release_workflow.py -q        # T1: 7 passed
/tmp/dev/bin/pytest tests/test_verify_install.py -q          # T1: 42 funções; 2 casos novos
/tmp/dev/bin/pytest tests/test_release_checks.py -q          # T2: 10 passed
/tmp/dev/bin/pytest tests/test_action_workflow.py tests/test_verify_install_workflow.py tests/test_packaging.py -q
/tmp/dev/bin/pytest                                          # suíte toda verde
sh scripts/verify-install.sh                                 # T1: 15 ok
(cd website && npm ci && npm run build && npm test)          # T2 e T3
```

## Anexos
```sh
cd /workspace/dispatch/u9-tN && sha256sum -c ../u9-tN.SHA256SUMS   # no repo: comparar os mesmos caminhos
```

## O que não roda localmente
- A matriz de 4 plataformas. Só no E0 (`dry_run`), disparado pelo Emerson.
