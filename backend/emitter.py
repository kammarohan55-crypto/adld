# backend/emitter.py
"""
Operand parsing and resolution helpers for the ALP assembler/interpreter.

Provides:
 - parse_operand(token: str, symbols: dict) -> operand_dict
 - resolve_effective_address(operand: dict, state: dict) -> int
 - operand_to_value(operand: dict, state: dict) -> int
 - read_word(mem: bytearray, addr: int) -> int
 - write_word(mem: bytearray, addr: int, value: int) -> None

State expected by resolve/operand_to_value:
{
  "registers": { "R0": int, "R1": int, ..., "SP": int, "FP": int, ...},
  "memory": bytearray,
  "symbols": { "LABEL": addr, ... }
}

Notes:
 - All word accesses are 32-bit little-endian.
 - autoinc / autodec modes will update the register inside state (this matches usual semantics).
 - For label-mode operands, if the symbol value is present in operand['value'] it will be used,
   otherwise the state's symbol table will be checked.
"""
from typing import Dict, Any, Optional

from . import assembler  # reuse parsing helper already in assembler
from .alp_spec import WORD_BYTES, ENDIAN

# Public wrapper for parsing an operand token string into the canonical operand dict
def parse_operand(token: str, symbols: Dict[str,int]) -> Dict[str, Any]:
    """
    Parse a textual operand token into an operand dict.

    This wraps assembler._parse_operand_token for reuse.
    """
    return assembler._parse_operand_token(token, symbols)

def read_word(mem: bytearray, addr: int) -> int:
    """Read 4 bytes from mem at addr as unsigned 32-bit little-endian integer."""
    if addr < 0 or addr + WORD_BYTES > len(mem):
        raise IndexError(f"read_word: address {addr} out of bounds (mem size {len(mem)})")
    b = mem[addr:addr+WORD_BYTES]
    # little-endian unsigned
    return int.from_bytes(b, byteorder='little', signed=False)

def write_word(mem: bytearray, addr: int, value: int) -> None:
    """Write 4 bytes little-endian into mem at addr."""
    if addr < 0 or addr + WORD_BYTES > len(mem):
        raise IndexError(f"write_word: address {addr} out of bounds (mem size {len(mem)})")
    mem[addr:addr+WORD_BYTES] = int(value & 0xFFFFFFFF).to_bytes(WORD_BYTES, byteorder='little', signed=False)

def resolve_effective_address(operand: Dict[str,Any], state: Dict[str,Any]) -> Optional[int]:
    """
    For memory-style operands, compute the effective address.
    May mutate state for autoinc/autodec modes (updates registers).
    Returns the computed address or None if operand is not a memory/addressing type.
    """
    mode = operand.get("mode")
    regs = state.get("registers", {})
    symbols = state.get("symbols", {})

    if mode == "indirect":
        reg = operand["reg"].upper()
        return int(regs.get(reg, 0))
    if mode == "indexed":
        reg = operand["reg"].upper()
        offset = int(operand.get("offset", 0))
        return int(regs.get(reg, 0)) + offset
    if mode == "autoinc":
        reg = operand["reg"].upper()
        addr = int(regs.get(reg, 0))
        # increment after use
        regs[reg] = addr + WORD_BYTES
        return addr
    if mode == "autodec":
        reg = operand["reg"].upper()
        # decrement before use
        newval = int(regs.get(reg, 0)) - WORD_BYTES
        regs[reg] = newval
        return newval
    if mode == "label":
        # operand may contain 'value' set by assembler pass; fallback to state's symbols
        if "value" in operand and operand["value"] is not None:
            return int(operand["value"])
        name = operand.get("name")
        if name in symbols:
            return int(symbols[name])
        return None
    if mode == "reg":
        # treat register as an address when used as destination/memory base by caller
        reg = operand["name"].upper()
        return int(regs.get(reg, 0))
    # immediate or other modes are not addresses
    return None

def operand_to_value(operand: Dict[str,Any], state: Dict[str,Any]) -> int:
    """
    Resolve operand to a concrete integer value.
    This reads registers or memory as needed.
    For autoinc/autodec this will update registers in the provided state.
    """
    mode = operand.get("mode")
    mem = state.get("memory")
    regs = state.get("registers", {})
    symbols = state.get("symbols", {})

    if mode == "empty":
        raise ValueError("Empty operand")
    if mode == "immediate":
        return int(operand["value"])
    if mode == "immediate_label":
        # immediate with label name, lookup symbol if available
        if "value" in operand and operand["value"] is not None:
            return int(operand["value"])
        name = operand.get("name")
        if name in symbols:
            return int(symbols[name])
        raise KeyError(f"Undefined immediate label: {name}")
    if mode == "reg":
        name = operand["name"].upper()
        return int(regs.get(name, 0))
    # Memory addressing forms (including label): compute effective address and read word
    addr = resolve_effective_address(operand, state)
    if addr is None:
        raise ValueError(f"Operand {operand} cannot be resolved to a value")
    # read from memory
    return read_word(mem, addr)

