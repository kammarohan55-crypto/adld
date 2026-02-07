# backend/stack_model.py
"""
Stack-frame helper utilities for ALP interpreter / visualizer.

These helpers operate on the interpreter `state` dict used throughout the project:
state = {
  "registers": { "R0": int, ..., "SP": int, "FP": int, "PC": int, "FLAGS": {...} },
  "memory": bytearray,
  "symbols": {...}
}

Helpers accept an `emit` callback for emitting events in the engine's event format:
    emit(evt_type: str, description: str, data: dict)

If emit is None, helpers will silently perform state changes without emitting events
(helps with unit tests).

Provided functions:
 - push_return_address(state, ret_addr, emit=None)
 - push_saved_fp(state, emit=None)
 - set_frame_pointer(state, emit=None)
 - allocate_locals(state, nbytes, emit=None)
 - pop_frame(state, emit=None) -> returns ret_addr (int)

Notes:
 - Uses WORD_BYTES from alp_spec for all word operations.
 - Uses emitter.write_word/read_word for safe memory access.
 - These helpers mirror the push/pop ordering used by engine_alp (push return addr, push old FP).
"""

from typing import Dict, Any, Optional, Callable
from .alp_spec import WORD_BYTES
from .emitter import write_word, read_word

EventEmitFn = Optional[Callable[[str, str, Dict[str,Any]], None]]

def _emit_or_noop(emit: EventEmitFn, typ: str, desc: str, data: Dict[str,Any]) -> None:
    if emit:
        emit(typ, desc, data)

def push_return_address(state: Dict[str,Any], ret_addr: int, emit: EventEmitFn = None) -> None:
    """
    Push a 4-byte return address onto the stack (decrement SP then write).
    Emits 'push' and 'reg_update' events when emit provided.
    """
    regs = state["registers"]
    mem = state["memory"]
    sp_before = int(regs["SP"])
    new_sp = sp_before - WORD_BYTES
    if new_sp < 0:
        raise RuntimeError("Stack overflow in push_return_address")
    regs["SP"] = new_sp
    write_word(mem, new_sp, int(ret_addr) & 0xFFFFFFFF)
    _emit_or_noop(emit, "push", f"push return_address -> addr {new_sp}", {"addr": new_sp, "value": ret_addr, "what":"return_address"})
    _emit_or_noop(emit, "reg_update", f"SP <- {new_sp}", {"reg":"SP","old":sp_before,"new":new_sp})

def push_saved_fp(state: Dict[str,Any], emit: EventEmitFn = None) -> None:
    """
    Push the current FP value onto the stack (decrement SP then write).
    Emits events when emit provided.
    """
    regs = state["registers"]
    mem = state["memory"]
    sp_before = int(regs["SP"])
    new_sp = sp_before - WORD_BYTES
    if new_sp < 0:
        raise RuntimeError("Stack overflow in push_saved_fp")
    # old FP value
    old_fp = int(regs.get("FP", 0))
    regs["SP"] = new_sp
    write_word(mem, new_sp, old_fp & 0xFFFFFFFF)
    _emit_or_noop(emit, "push", f"push saved_fp -> addr {new_sp}", {"addr": new_sp, "value": old_fp, "what":"saved_fp"})
    _emit_or_noop(emit, "reg_update", f"SP <- {new_sp}", {"reg":"SP","old":sp_before,"new":new_sp})

def set_frame_pointer(state: Dict[str,Any], emit: EventEmitFn = None) -> None:
    """
    Set FP to current SP and emit reg_update event.
    """
    regs = state["registers"]
    old_fp = int(regs.get("FP", 0))
    new_fp = int(regs["SP"])
    regs["FP"] = new_fp
    _emit_or_noop(emit, "reg_update", f"FP <- {new_fp}", {"reg":"FP","old":old_fp,"new":new_fp})

def allocate_locals(state: Dict[str,Any], nbytes: int, emit: EventEmitFn = None) -> None:
    """
    Allocate local space by decrementing SP by nbytes (should be multiple of WORD_BYTES).
    Zero-fill the allocated memory region.
    Emits reg_update and mem_write-like events for the allocation (one summary event).
    """
    if nbytes < 0:
        raise ValueError("allocate_locals: nbytes must be non-negative")
    regs = state["registers"]
    mem = state["memory"]
    sp_before = int(regs["SP"])
    new_sp = sp_before - int(nbytes)
    if new_sp < 0:
        raise RuntimeError("Stack overflow in allocate_locals")
    # zero-fill (safely extend mem if needed)
    if new_sp < 0:
        raise RuntimeError("allocate_locals would underflow memory")
    regs["SP"] = new_sp
    # Ensure mem large enough (should already be ensured by engine)
    if new_sp < 0:
        raise RuntimeError("Memory too small for allocation")
    # Zero the allocated area (mem slice new_sp:sp_before)
    for i in range(new_sp, sp_before):
        mem[i] = 0
    _emit_or_noop(emit, "allocate_locals", f"allocate locals {nbytes} bytes -> SP {new_sp}", {"old_sp":sp_before,"new_sp":new_sp,"size":nbytes})

def pop_frame(state: Dict[str,Any], emit: EventEmitFn = None) -> int:
    """
    Pop a frame: restore SP to FP (deallocate locals), then pop saved_fp and return_address, restore FP and return ret_addr.
    Returns the integer return address.
    Emits pop/reg_update/return events via emit if provided.
    """
    regs = state["registers"]
    mem = state["memory"]
    # First, deallocate locals by restoring SP to FP
    fp_val = int(regs.get("FP", 0))
    old_sp = int(regs["SP"])
    if old_sp != fp_val:
        regs["SP"] = fp_val
        _emit_or_noop(emit, "reg_update", f"SP <- {fp_val} (deallocate locals)", {"reg":"SP","old":old_sp,"new":fp_val})
    
    sp_before = int(regs["SP"])
    # pop saved_fp (read at SP then increment)
    if sp_before + WORD_BYTES > len(mem):
        raise RuntimeError("Stack underflow during pop_frame (saved_fp)")
    saved_fp = read_word(mem, sp_before)
    _emit_or_noop(emit, "pop", f"pop saved_fp <- addr {sp_before} value {saved_fp}", {"addr":sp_before,"value":saved_fp,"what":"saved_fp"})
    new_sp = sp_before + WORD_BYTES
    regs["SP"] = new_sp
    _emit_or_noop(emit, "reg_update", f"SP <- {new_sp}", {"reg":"SP","old":sp_before,"new":new_sp})
    # restore FP
    old_fp = int(regs.get("FP", 0))
    regs["FP"] = saved_fp
    _emit_or_noop(emit, "reg_update", f"FP restored <- {saved_fp}", {"reg":"FP","old":old_fp,"new":saved_fp})
    # pop return address
    sp_now = int(regs["SP"])
    if sp_now + WORD_BYTES > len(mem):
        raise RuntimeError("Stack underflow during pop_frame (return_address)")
    ret_addr = read_word(mem, sp_now)
    _emit_or_noop(emit, "pop", f"pop return_address <- addr {sp_now} value {ret_addr}", {"addr":sp_now,"value":ret_addr,"what":"return_address"})
    regs["SP"] = sp_now + WORD_BYTES
    _emit_or_noop(emit, "reg_update", f"SP <- {regs['SP']}", {"reg":"SP","old":sp_now,"new":regs["SP"]})
    _emit_or_noop(emit, "return", f"return to {ret_addr}", {"to": ret_addr})
    return int(ret_addr)

