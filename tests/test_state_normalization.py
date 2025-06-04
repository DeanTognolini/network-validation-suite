import os
import sys
import types
import pytest

# Add repository root to path so modules can be imported when running tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Stub out optional dependencies used in modules so imports succeed during unit tests
pyats_mod = types.ModuleType('pyats')
aetest_mod = types.ModuleType('pyats.aetest')
setattr(aetest_mod, 'CommonSetup', type('CommonSetup', (), {}))
setattr(aetest_mod, 'Testcase', type('Testcase', (), {}))
setattr(aetest_mod, 'CommonCleanup', type('CommonCleanup', (), {}))
setattr(aetest_mod, 'subsection', lambda *args, **kwargs: (lambda func: func))
setattr(aetest_mod, 'test', lambda *args, **kwargs: (lambda func: func))
pyats_mod.aetest = aetest_mod
sys.modules.setdefault('pyats', pyats_mod)
sys.modules.setdefault('pyats.aetest', aetest_mod)
genie_mod = types.ModuleType('genie')
testbed_mod = types.ModuleType('genie.testbed')
setattr(testbed_mod, 'load', lambda *args, **kwargs: None)
genie_mod.testbed = testbed_mod
sys.modules.setdefault('genie', genie_mod)
sys.modules.setdefault('genie.testbed', testbed_mod)
abstraction_mod = types.ModuleType('genie.libs.abstraction')
setattr(abstraction_mod, 'Lookup', type('Lookup', (), {}))
sys.modules.setdefault('genie.libs.abstraction', abstraction_mod)

from ospf_nei_check.ospf_nei_check import normalize_ospf_state
from bgp_peer_check.bgp_peer_check import normalize_bgp_state


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("full/dr", "full/dr"),
        ("full/bdr", "full/bdr"),
        ("full/  -", "full"),
        ("full/", "full"),
        (" full ", "full"),
        (" full/BDr ", "full/bdr"),
    ],
)
def test_normalize_ospf_state(raw, expected):
    assert normalize_ospf_state(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Established", "established"),
        (" established ", "established"),
        ("Idle", "idle"),
    ],
)
def test_normalize_bgp_state(raw, expected):
    assert normalize_bgp_state(raw) == expected
