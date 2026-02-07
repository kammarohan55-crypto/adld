# backend/alp_spec.py
"""
ALP (Assembly-Like Program) specification for the pedagogical ALP visualizer.

This module is the canonical source-of-truth describing:
 - word size and endianness
 - register set
 - assembler directives
 - supported addressing modes and their textual syntax
 - instruction set (mnemonics + short semantics)
 - canonical calling convention and stack-frame layout
 - small helper utilities for use by assembler/interpreter/tests

NOTE: This file is intentionally both machine- and human-readable: code imports constants,
and implementers/readers get helpful comments and examples.

Example ALP snippet (for tests and docs):

ORIGIN 100
MOVE N, R1
MOVE #NUM1, R2
MOVE #0, R0
LOOP:
  ADD (R2), R0
  ADD #4, R2
  DECREMENT R1
  BRANCH >0, LOOP
MOVE R0, SUM

ORIGIN 200
SUM: RESERVE 4
N: DATAWORD 5
NUM1: DATAWORD 2,5,7,-1,30
END
"""

from typing import List, Dict

# Machine constants
WORD_BYTES: int = 4
ENDIAN: str = "little"   # 'little' or 'big'

# Register set (names). Implementations should provide storage for these names.
REGISTERS: List[str] = [
    "R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7",
    "SP", "FP", "PC", "FLAGS"
]

# Assembler directives supported
DIRECTIVES: List[str] = [
    "ORIGIN",    # ORIGIN <address>
    "DATAWORD",  # DATAWORD v1[,v2,...]
    "RESERVE",   # RESERVE <n_bytes>
    "END"        # end of assembly
]

# Addressing mode descriptions (human-readable forms used by the assembler docs)
ADDRESSING_MODES: Dict[str, str] = {
    "immediate": "#num or #label",     # e.g. #4 or #N
    "register": "Rn (e.g. R0, R1)",
    "indirect": "(Rn) (memory at address in Rn)",
    "autoinc": "(Rn)+ (post-increment by WORD_BYTES)",
    "autodec": "-(Rn) (pre-decrement by WORD_BYTES)",
    "indexed": "offset(Rn) (e.g. 12(R0))",
    "label": "LABEL (direct addressing to label address)"
}

# Instruction set supported (mnemonics list). Each instruction's detailed semantics
# should be implemented by the assembler/interpreter according to the summary below.
INSTRUCTIONS: List[str] = [
    # Data transfer and stack helpers
    "MOVE",    # MOVE src, dst
    "PUSH",    # pseudo -> MOVE src, -(SP)
    "POP",     # pseudo -> MOVE (SP)+, dst
    "MOVEM",   # MOVEM reglist, -(SP) or MOVEM (SP)+, reglist

    # Arithmetic
    "ADD",     # ADD src, dst -> dst = dst + src
    "SUB",     # SUB src, dst -> dst = dst - src
    "MUL",     # MUL src, dst -> optional: dst = dst * src
    "DIV",     # DIV src, dst -> optional: integer division

    # Logical / clearing helpers
    "CLR",     # CLR Rn  -> MOVE #0, Rn
    "INCREMENT", "DECREMENT",  # aliases for ADD #1 and ADD #-1

    # Compare & Branch
    "COMPARE", # COMPARE op1, op2 -> sets FLAGS based on op1 - op2
    "BRANCH",  # BRANCH cond, LABEL or BRANCH LABEL (unconditional)
    "BGT", "BLT", "BEQ", "BNE",  # convenience mnemonics

    # Subroutine control
    "CALL",    # CALL LABEL -> push return addr, push old FP, set FP, PC <- label
    "RETURN", "RET"  # RETURN -> restore FP and PC (pop) and possibly saved regs
]

# Calling convention and canonical stack-frame layout (textual)
CALLING_CONVENTION: Dict[str, object] = {
    "stack_grows": "down",        # stack grows toward lower addresses
    "word_bytes": WORD_BYTES,
    "frame_layout_high_to_low": [
        "caller_params (higher addresses)",
        "return_address (pushed by CALL)",
        "saved_FP (old FP pushed)",
        "saved_registers  (callee may push a range of registers)",
        "local_variables (allocated by subtracting SP)"
    ],
    # Detailed step semantics for CALL:
    #  - Caller may push arguments (if stack-params mode)
    #  - CALL macro:
    #      1) push return_address (address of next instruction)
    #      2) push old FP
    #      3) set FP = SP
    #      4) optionally push saved registers (MOVEM) as callee-saved
    #      5) allocate locals by SP = SP - locals_size
    #  - RETURN macro:
    #      1) deallocate locals (SP += locals_size)
    #      2) restore saved registers (MOVEM pop)
    #      3) restore old FP (pop)
    #      4) pop return_address into PC (jump back)
}

# Flags semantics summary (as used with COMPARE)
FLAGS_DESCRIPTION: Dict[str, str] = {
    "Z": "Zero flag (1 if last result == 0, else 0)",
    "S": "Sign flag (set to positive/negative/zero indicator, e.g., -1/0/1)",
    # Note: an implementation may encode FLAGS as a dict rather than a bitmask.
}

# Helper helpers for implementers/tests
def is_register(token: str) -> bool:
    """Return True if token is a known register name."""
    return token.upper() in REGISTERS

def canonical_register(token: str) -> str:
    """Return canonical register name (upper-case)."""
    return token.upper()

# Example: token patterns (for assembler use)
# - Immediate: ^#-?\d+$ or ^#LABEL$
# - Register: ^R[0-9]+$ or SP/FP/PC/FLAGS
# - Indirect: ^\(\s*R[0-9]+\s*\)$
# - Autoinc: ^\(\s*R[0-9]+\s*\)\+$  (post-increment)
# - Autodec: ^-\(\s*R[0-9]+\s*\)$   (pre-decrement)
# - Indexed: ^-?\d+\s*\(\s*R[0-9]+\s*\)$

# Default initial stack top multiplier for simulators that need a default:
# (interpreters may override to match memory size)
DEFAULT_STACK_TOP_MULTIPLIER = 4

# Small note: Some assembler tests may assume that instruction address increments
# deterministically by WORD_BYTES (4) per instruction for label assignment.
# The assembler will use this assumption when assigning addresses in pass 1.
