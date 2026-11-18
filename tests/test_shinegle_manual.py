"""The SG1810 parameter and fault YAML files load, are complete, and the tables doc matches."""

from teryx import shinegle_manual as M


def test_params_have_the_basics():
    params = M.load_params()
    assert len(params) >= 60
    for p in params:
        assert {"page", "name", "cn", "en", "remark"} <= set(p), p
        assert str(p["page"]) in "0123456789abcdef"
    keys = [(p["page"], p["name"]) for p in params]
    assert len(keys) == len(set(keys))
    green = {p["name"] for p in params if p.get("adjustable")}
    assert green == {"F_Spd", "R_Spd", "F_Rat", "R_Rat", "DecRat", "B_Rat"}


def test_regen_parameters_are_there():
    by = {(p["page"], p["name"]): p for p in M.load_params()}
    assert "Regenerative" in by[("9", "B_Cur")]["remark"]
    assert by[("4", "B_Rat")]["value"] == "12"


def test_fault_codes_cover_1_to_46_once():
    seen = []
    for f in M.load_faults():
        seen += list(M._codes(f))
        assert {"cn", "en"} <= set(f)
    assert sorted(seen) == list(range(1, 47))


def test_fault_lookup():
    assert M.fault(7)["en"] == "Phase V fault"
    assert M.fault(18)["en"] == "Current sensor 2 fault"
    assert M.fault(33)["en"] == "System error 2"
    assert M.fault(0) is None and M.fault(99) is None


def test_tables_doc_is_up_to_date():
    assert M.OUTPUT.read_text(encoding="utf-8") == M.render(), "run: python -m teryx shinegle-manual"
