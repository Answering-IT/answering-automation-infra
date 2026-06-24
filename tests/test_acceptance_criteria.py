import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from parse_github_issues import extract_acceptance_criteria  # noqa: E402


@pytest.mark.smoke
def test_extract_acceptance_criteria_english():
    body = "## Acceptance Criteria\n- [ ] build passes\n- [ ] lint passes\n"
    assert extract_acceptance_criteria(body) == ["build passes", "lint passes"]


@pytest.mark.smoke
def test_extract_acceptance_criteria_spanish():
    """The /spec skill emits Spanish headers; the parser must accept them."""
    body = "## Criterios de Aceptación\n- [ ] build pasa\n- [ ] lint pasa\n"
    assert extract_acceptance_criteria(body) == ["build pasa", "lint pasa"]


@pytest.mark.smoke
def test_extract_acceptance_criteria_spanish_no_accent():
    body = "## Criterios de Aceptacion\n- [ ] uno\n"
    assert extract_acceptance_criteria(body) == ["uno"]
