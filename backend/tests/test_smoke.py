# backend/tests/test_smoke.py
def test_imports():
    # Smoke test to ensure backend package imports
    import importlib
    importlib.import_module("backend.app")  # Flask app
    importlib.import_module("backend.assembler")  # ALP assembler
    importlib.import_module("backend.engine_alp")  # ALP engine
    importlib.import_module("backend.alp_spec")  # ALP spec constants
    importlib.import_module("backend.emitter")  # Event emitter
    assert True
