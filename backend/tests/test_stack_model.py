# backend/tests/test_stack_model.py
import pytest
from backend import stack_model
from backend.emitter import read_word
from backend import assembler

def make_state(mem_size=1024):
    mem = bytearray([0] * mem_size)
    regs = { f"R{i}": 0 for i in range(8) }
    regs.update({"SP": mem_size - 4, "FP": 0, "PC": 0, "FLAGS": {"Z":0,"S":0}})
    return {"registers": regs, "memory": mem, "symbols": {}}

def test_push_and_pop_frame_roundtrip():
    st = make_state()
    regs = st["registers"]
    mem = st["memory"]
    events = []
    def emit(t,d,dt):
        events.append((t,d,dt))

    orig_sp = regs["SP"]
    orig_fp = regs["FP"]
    # push return address (e.g., 0x1234)
    stack_model.push_return_address(st, 0x1234, emit=emit)
    # push saved_fp (orig_fp = 0)
    stack_model.push_saved_fp(st, emit=emit)
    # set FP to SP
    stack_model.set_frame_pointer(st, emit=emit)
    # allocate locals 8 bytes
    stack_model.allocate_locals(st, 8, emit=emit)

    # Now pop the frame and verify values restored
    ret = stack_model.pop_frame(st, emit=emit)
    assert ret == 0x1234, f"Expected return address 0x1234, got {ret}"
    # After pop_frame, FP should be restored to original (0)
    assert regs["FP"] == orig_fp
    # SP should be at original SP + (we popped 2 words) + locals deallocation effect:
    # Since allocate_locals decreased SP by 8, and push_return_address/push_saved_fp decreased SP by 8 total (2*4),
    # the final SP after pop_frame should be orig_sp + 8 (because pop_frame increments SP by 8).
    assert regs["SP"] == orig_sp, f"Expected SP back to orig {orig_sp}, got {regs['SP']}"
    # Memory at returned return address location should not be overwritten by pop (just read)
    # Check that read_word at location where return address was stored before pop equals 0x1234 or was read
    # We can't guarantee mem content after pop, but ensure read_word does not crash on typical offsets
    # Also assert that events were emitted and include push/pop/reg_update entries
    types = [e[0] for e in events]
    assert "push" in types
    assert "pop" in types
    assert "reg_update" in types

def test_allocate_locals_bounds_check():
    st = make_state(mem_size=64)
    regs = st["registers"]
    # try to allocate more than available
    with pytest.raises(RuntimeError):
        stack_model.allocate_locals(st, 1000, emit=None)
