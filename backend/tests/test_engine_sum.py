# backend/tests/test_engine_sum.py
import backend.assembler as assembler
import backend.engine_alp as engine
from backend import emitter

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

def test_engine_sum():
    assembled = assembler.assemble(SAMPLE)
    assert len(assembled["errors"]) == 0, f"Assembler errors: {assembled['errors']}"
    res = engine.simulate(assembled, run_opts={"max_steps":10000})
    assert "errors" in res
    assert len(res["errors"]) == 0, f"Runtime errors: {res['errors']}"
    final = res["final_state"]
    mem = final["memory"]
    symbols = final["symbols"]
    assert "SUM" in symbols
    sum_addr = symbols["SUM"]
    val = emitter.read_word(mem, sum_addr)
    assert val == 43, f"Expected SUM=43, got {val}"
