# backend/tests/test_operand.py
import pytest
from backend import emitter
from backend import assembler

def make_state(mem_size=512):
    # simple state with registers and zeroed memory
    regs = {f"R{i}": 0 for i in range(8)}
    regs.update({"SP": mem_size - 4, "FP": 0, "PC": 0})
    mem = bytearray([0] * mem_size)
    return {"registers": regs, "memory": mem, "symbols": {}}

def write_word(mem, addr, value):
    mem[addr:addr+4] = int(value & 0xFFFFFFFF).to_bytes(4, byteorder='little')

def test_parse_basic_immediate_and_register():
    symbols = {"L": 100}
    op1 = emitter.parse_operand("#5", symbols)
    assert op1["mode"] == "immediate" and op1["value"] == 5
    op2 = emitter.parse_operand("R3", symbols)
    assert op2["mode"] == "reg" and op2["name"].upper() == "R3"
    op3 = emitter.parse_operand("L", symbols)
    assert op3["mode"] == "label" and op3["name"] == "L"

def test_operand_value_and_memory_access():
    st = make_state(mem_size=256)
    regs = st["registers"]
    mem = st["memory"]
    # prepare memory at address 100
    write_word(mem, 100, 0x11223344)
    regs["R0"] = 100
    # indirect (R0)
    op_ind = emitter.parse_operand("(R0)", {})
    val = emitter.operand_to_value(op_ind, st)
    assert val == 0x11223344
    # indexed 12(R0)
    write_word(mem, 112, 0x01020304)
    op_idx = emitter.parse_operand("12(R0)", {})
    val2 = emitter.operand_to_value(op_idx, st)
    assert val2 == 0x01020304

def test_autoinc_and_autodec():
    st = make_state(mem_size=256)
    regs = st["registers"]
    mem = st["memory"]
    # set R1 to 120, R2 to 140
    regs["R1"] = 120
    regs["R2"] = 140
    write_word(mem, 120, 0xAAAAAAAA)
    write_word(mem, 136, 0xBBBBBBBB)  # for autodec we'll use 140 - 4 = 136
    # autoinc (R1)+ should read at 120 then set R1 to 124
    op_ai = emitter.parse_operand("(R1)+", {})
    v_ai = emitter.operand_to_value(op_ai, st)
    assert v_ai == 0xAAAAAAAA
    assert regs["R1"] == 120 + 4
    # autodec -(R2) should decrement R2 to 136 and read that address
    op_ad = emitter.parse_operand("-(R2)", {})
    v_ad = emitter.operand_to_value(op_ad, st)
    assert v_ad == 0xBBBBBBBB
    assert regs["R2"] == 136

def test_label_address_resolution_from_state():
    st = make_state()
    st["symbols"]["FOO"] = 200
    op = emitter.parse_operand("FOO", st["symbols"])
    assert op["mode"] == "label"
    # resolve address via resolve_effective_address
    addr = emitter.resolve_effective_address(op, st)
    assert addr == 200
    # also operand_to_value will read memory at that address; put word there
    write_word(st["memory"], 200, 0xDEADBEEF)
    val = emitter.operand_to_value(op, st)
    assert val == 0xDEADBEEF
