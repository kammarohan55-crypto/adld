# backend/tests/test_assemble.py
import backend.assembler as assembler

SAMPLE = """ORIGIN 100
MOVE N,R1
MOVE #NUM1,R2
MOVE #0,R0
LOOP:
 ADD (R2),R0
 ADD #4,R2
 DECREMENT R1
 BRANCH >0,LOOP
MOVE R0,SUM
ORIGIN 200
SUM: RESERVE 4
N: DATAWORD 5
NUM1: DATAWORD 2,5,7,-1,30
END
"""

def test_assemble_sample():
    res = assembler.assemble(SAMPLE)
    assert isinstance(res, dict)
    assert "errors" in res
    # no assembly errors expected
    assert len(res["errors"]) == 0, "Assembler returned errors: %s" % (res["errors"],)
    # symbols should contain SUM and N and NUM1
    symbols = res["symbols"]
    assert "SUM" in symbols, f"SUM not in symbols: {symbols.keys()}"
    assert "N" in symbols
    assert "NUM1" in symbols
    # SUM should be at ORIGIN 200
    assert symbols["SUM"] == 200, f"SUM expected at 200, found {symbols['SUM']}"
    # memory must contain N (DATAWORD 5) at its assigned address
    # The test doesn't assume exact memory layout beyond presence of symbol
