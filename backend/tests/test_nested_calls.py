# backend/tests/test_nested_calls.py
import backend.assembler as assembler
import backend.engine_alp as engine
from backend import emitter

# ALP program:
# main calls sub1; sub1 calls sub2; sub2 writes RESULT; returns; test checks RESULT
SAMPLE = """ORIGIN 100
CALL SUB1
HALT: ; no-op/stop if needed; but engine stops when PC has no instruction
ORIGIN 200
SUB1:
  CALL SUB2
  RETURN
SUB2:
  MOVE #123, R0
  MOVE R0, RESULT
  RETURN
ORIGIN 300
RESULT: RESERVE 4
END
"""

def test_nested_calls_and_result():
    assembled = assembler.assemble(SAMPLE)
    assert len(assembled["errors"]) == 0, f"Assembler errors: {assembled['errors']}"
    res = engine.simulate(assembled, run_opts={"max_steps":10000})
    assert len(res["errors"]) == 0, f"Runtime errors: {res['errors']}"
    final = res["final_state"]
    mem = final["memory"]
    symbols = final["symbols"]
    assert "RESULT" in symbols
    result_addr = symbols["RESULT"]
    val = emitter.read_word(mem, result_addr)
    assert val == 123, f"Expected RESULT=123, got {val}"
    # Also assert there were push_frame and pop_frame events in the trace (nested frames)
    typelist = [e["type"] for e in res["events"]]
    assert "push_frame" in typelist and "pop" in typelist
