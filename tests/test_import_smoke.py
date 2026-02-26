import sys

import pytest


@pytest.mark.skipif(sys.version_info < (3, 10), reason='Smoke import targets runtime Python 3.10+ (Docker uses 3.12)')
def test_schemas_import_smoke():
    from api.app import schemas  # noqa: F401

    assert schemas.ManualCostCreate is not None
    assert schemas.ManualCostUpdate is not None
