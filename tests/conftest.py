"""O fixture Python tem os próprios testes; a suíte do plugin não os coleta."""

import os

collect_ignore = ["fixtures"]

# `coverage run` não mede o subprocesso da CLI. O rc fica em BOB_COVERAGE_RC.
_coverage_rc = os.environ.get("BOB_COVERAGE_RC")
if _coverage_rc:
    os.environ["COVERAGE_PROCESS_START"] = _coverage_rc
