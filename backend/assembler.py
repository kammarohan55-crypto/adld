# backend/assembler.py
"""
Two-pass assembler for the ALP pedagogical dialect.

Public function:
    assemble(source: str) -> dict

Returns a dict:
{
  "instructions": [ { "addr": int, "mnemonic": str, "operands": [operand_dict,...], "source": str }, ... ],
  "memory": bytearray,          # little-endian memory image containing DATAWORD/RESERVE regions
  "symbols": { "LABEL": addr, ... },
  "errors": [ "error msg", ... ]
}

Notes / assumptions:
- Instruction size is assumed 4 bytes for address allocation.
- DATAWORD writes 4 bytes per value (little-endian).
- RESERVE reserves n bytes (zero-filled).
- ORIGIN sets the assembly address pointer.
- Labels are "NAME:" at start of a line (whitespace permitted).
- Comments begin with ';' and extend to end of line.
"""

import re
from typing import List, Dict, Tuple, Optional

from .alp_spec import WORD_BYTES

# Regex helpers
_RE_LABEL = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:;.*)?$')
_RE_DIRECTIVE = re.compile(r'^\s*(ORIGIN|DATAWORD|RESERVE|END)\b', re.IGNORECASE)
_RE_ORIGIN = re.compile(r'^\s*ORIGIN\s+([0-9]+)\s*$', re.IGNORECASE)
_RE_DATAWORD = re.compile(r'^\s*DATAWORD\s+(.*)$', re.IGNORECASE)
_RE_RESERVE = re.compile(r'^\s*RESERVE\s+([0-9]+)\s*$', re.IGNORECASE)
_RE_INSTRUCTION = re.compile(r'^\s*([A-Za-z]+)\b(.*)$')  # mnemonic then rest

# Operand patterns (simple)
_RE_IMMEDIATE = re.compile(r'^\s*#(-?\d+|[A-Za-z_][A-Za-z0-9_]*)\s*$')
_RE_REGISTER = re.compile(r'^\s*(R[0-9]+|SP|FP|PC|FLAGS)\s*$', re.IGNORECASE)
_RE_INDIRECT = re.compile(r'^\s*\(\s*(R[0-9]+)\s*\)\s*$', re.IGNORECASE)
_RE_AUTOINC = re.compile(r'^\s*\(\s*(R[0-9]+)\s*\)\+\s*$', re.IGNORECASE)
_RE_AUTODEC = re.compile(r'^\s*-\(\s*(R[0-9]+)\s*\)\s*$', re.IGNORECASE)
_RE_INDEXED = re.compile(r'^\s*(-?\d+)\s*\(\s*(R[0-9]+)\s*\)\s*$', re.IGNORECASE)
_RE_LABELONLY = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*$')

def _strip_comments(line: str) -> str:
    # Comments start with ';'
    if ';' in line:
        return line.split(';', 1)[0]
    return line

def _tokenize_operands(opstr: str) -> List[str]:
    # Split operands by comma, but tolerate commas inside parentheses by a simple approach
    # since our operand grammar doesn't include nested commas, a plain split is fine.
    parts = [p.strip() for p in opstr.split(',') if p.strip() != ""]
    return parts

def _parse_operand_token(token: str, symbols: Dict[str,int]) -> Dict:
    """
    Returns an operand dict with fields:
      - mode: one of immediate, reg, indirect, autoinc, autodec, indexed, label
      - value / name / reg / offset as appropriate
    If a label is referenced and present in symbols, include its numeric value.
    """
    t = token.strip()
    if t == "":
        return {"mode":"empty"}
    m = _RE_IMMEDIATE.match(t)
    if m:
        lit = m.group(1)
        if re.match(r'^-?\d+$', lit):
            return {"mode":"immediate","value":int(lit)}
        else:
            # label immediate like #LABEL
            name = lit
            return {"mode":"immediate_label","name":name, "value": symbols.get(name)}
    m = _RE_REGISTER.match(t)
    if m:
        return {"mode":"reg","name":m.group(1).upper()}
    m = _RE_INDIRECT.match(t)
    if m:
        return {"mode":"indirect","reg":m.group(1).upper()}
    m = _RE_AUTOINC.match(t)
    if m:
        return {"mode":"autoinc","reg":m.group(1).upper()}
    m = _RE_AUTODEC.match(t)
    if m:
        return {"mode":"autodec","reg":m.group(1).upper()}
    m = _RE_INDEXED.match(t)
    if m:
        offset = int(m.group(1))
        reg = m.group(2).upper()
        return {"mode":"indexed","reg":reg,"offset":offset}
    m = _RE_LABELONLY.match(t)
    if m:
        name = m.group(1)
        return {"mode":"label","name":name, "value": symbols.get(name)}
    # Fallback: return as raw token to surface error later
    return {"mode":"unknown","token":t}

def _encode_word_le(value: int) -> bytes:
    # 32-bit signed integers -> 4 bytes little-endian
    # Keep values as unsigned representation for writing bytes
    return int(value & 0xFFFFFFFF).to_bytes(4, byteorder='little', signed=False)

def assemble(source: str) -> Dict:
    """
    Two-pass assembler.

    Returns:
      {
        "instructions": [ ... ],
        "memory": bytearray(...),
        "symbols": {...},
        "errors": [...]
      }
    """
    errors: List[str] = []
    lines = source.splitlines()
    # First pass: determine addresses (labels, data sizes) and collect raw parsed line info
    addr = 0
    origin_set = False
    symbol_table: Dict[str,int] = {}
    # We'll store a list of items in order for pass2. Each item: (type, content, line_no, raw_line, addr)
    # type in ("label","directive","instruction")
    items: List[Tuple[str, object, int, str, int]] = []
    current_addr = 0

    for i, raw in enumerate(lines, start=1):
        line = _strip_comments(raw).rstrip()
        if line.strip() == "":
            continue
        
        # Check if line starts with a label (NAME:)
        # Extract label if present and process the rest
        label_name = None
        if ':' in line:
            # Try to extract label
            colon_idx = line.index(':')
            potential_label = line[:colon_idx].strip()
            if potential_label and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', potential_label):
                label_name = potential_label
                if label_name in symbol_table:
                    errors.append(f"Line {i}: duplicate label {label_name}")
                else:
                    symbol_table[label_name] = current_addr
                items.append(("label", label_name, i, raw, current_addr))
                # Continue with rest of line after colon
                line = line[colon_idx+1:].strip()
                if line == "":
                    continue  # Label-only line
        
        # Now process directive or instruction
        # Directive?
        m_dir = _RE_DIRECTIVE.match(line)
        if m_dir:
            dirname = m_dir.group(1).upper()
            if dirname == "ORIGIN":
                m = _RE_ORIGIN.match(line)
                if not m:
                    errors.append(f"Line {i}: bad ORIGIN syntax")
                else:
                    origin_val = int(m.group(1))
                    current_addr = origin_val
                    origin_set = True
                    items.append(("directive", ("ORIGIN", origin_val), i, raw, current_addr))
            elif dirname == "DATAWORD":
                m = _RE_DATAWORD.match(line)
                if not m:
                    errors.append(f"Line {i}: bad DATAWORD syntax")
                else:
                    vals = m.group(1)
                    # split by commas
                    parts = [p.strip() for p in vals.split(',') if p.strip() != ""]
                    # count how many words emitted
                    nwords = len(parts)
                    items.append(("directive", ("DATAWORD", parts), i, raw, current_addr))
                    current_addr += WORD_BYTES * nwords
            elif dirname == "RESERVE":
                m = _RE_RESERVE.match(line)
                if not m:
                    errors.append(f"Line {i}: bad RESERVE syntax")
                else:
                    nbytes = int(m.group(1))
                    items.append(("directive", ("RESERVE", nbytes), i, raw, current_addr))
                    current_addr += nbytes
            elif dirname == "END":
                items.append(("directive", ("END", None), i, raw, current_addr))
                break
            else:
                errors.append(f"Line {i}: unknown directive {dirname}")
            continue
        # Otherwise treat as instruction (mnemonic + operands)
        m_inst = _RE_INSTRUCTION.match(line)
        if m_inst:
            mnemonic = m_inst.group(1).upper()
            rest = m_inst.group(2).strip()
            # We'll count every instruction as WORD_BYTES for address allocation
            items.append(("instruction", (mnemonic, rest), i, raw, current_addr))
            current_addr += WORD_BYTES
            continue
        # If nothing matched
        errors.append(f"Line {i}: unrecognized line: {line}")

    # PASS 1 done: we have symbol_table and items. Now build memory image entries and instructions list (pass2)
    # Build a map for data writes: list of (addr, bytes)
    data_writes: List[Tuple[int, bytes]] = []
    # We'll also keep track of reserved ranges to zero-fill
    reserved_ranges: List[Tuple[int,int]] = []

    instructions_out: List[Dict] = []

    # Second pass: process items and resolve operands with symbol_table
    # Reset current_addr for walking again
    # Note: a label item doesn't change address here; ORIGIN and directives handled by items.
    for typ, content, lineno, rawline, item_addr in items:
        if typ == "label":
            # label already recorded in pass1; nothing more to do
            continue
        if typ == "directive":
            dname, dval = content
            if dname == "ORIGIN":
                # nothing to emit; item_addr is already the origin
                continue
            if dname == "DATAWORD":
                parts: List[str] = dval
                addr_here = item_addr
                for p in parts:
                    # p may be a numeric literal or a label name
                    p_str = p.strip()
                    if re.match(r'^-?\d+$', p_str):
                        v = int(p_str)
                    else:
                        # label reference: if present in symbol table, get value, else leave None and record error
                        if p_str in symbol_table:
                            v = symbol_table[p_str]
                        else:
                            # forward ref or undefined label -> error
                            errors.append(f"Line {lineno}: DATAWORD references undefined label '{p_str}'")
                            v = 0
                    data_writes.append((addr_here, _encode_word_le(v)))
                    addr_here += WORD_BYTES
                continue
            if dname == "RESERVE":
                nbytes = dval
                reserved_ranges.append((item_addr, item_addr + nbytes))
                continue
            if dname == "END":
                break
            continue
        if typ == "instruction":
            mnemonic, rest = content
            # Tokenize operands
            ops = []
            if rest != "":
                operands = _tokenize_operands(rest)
                for tok in operands:
                    op = _parse_operand_token(tok, symbol_table)
                    ops.append(op)
            inst = {
                "addr": item_addr,
                "mnemonic": mnemonic,
                "operands": ops,
                "source": rawline.strip()
            }
            instructions_out.append(inst)
            continue

    # Determine memory size: max of data writes, reserved ranges, and highest instruction addr + WORD_BYTES
    max_addr = 0
    for (a, bts) in data_writes:
        if a + len(bts) - 1 > max_addr:
            max_addr = a + len(bts) - 1
    for (start, end) in reserved_ranges:
        if end - 1 > max_addr:
            max_addr = end - 1
    for inst in instructions_out:
        if inst["addr"] + WORD_BYTES - 1 > max_addr:
            max_addr = inst["addr"] + WORD_BYTES - 1

    # If nothing assembled, ensure at least one byte to avoid zero-length bytearray issues
    mem_size = max(max_addr + 1, 1)
    mem = bytearray([0] * mem_size)

    # Write data_writes into memory
    for (addr_write, bytes_val) in data_writes:
        if addr_write + len(bytes_val) > len(mem):
            errors.append(f"Data write at {addr_write} out of memory bounds (mem size {len(mem)})")
            continue
        mem[addr_write:addr_write+len(bytes_val)] = bytes_val

    # Zero-fill reserved ranges (already zeroed in mem allocation)
    # Build the final symbol table (already prepared)
    result = {
        "instructions": instructions_out,
        "memory": mem,
        "symbols": symbol_table,
        "errors": errors
    }
    return result
