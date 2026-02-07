# backend/engine_alp.py
"""
ALP interpreter / emulator + event emitter.

Public API:
    simulate(assembled: dict, run_opts: dict={}) -> dict
Returns:
    {
      "events": [ ... event dicts ... ],
      "final_state": { "registers": {...}, "memory": bytearray, "symbols": {...} },
      "errors": [...]
    }

Notes:
 - This interpreter works with assembler.assemble() output.
 - It emits fine-grained micro-events for every atomic change (reg_update, mem_read, mem_write, push, pop, instruction, compare, branch, call, return).
 - It tries to be conservative and safe: it extends memory to provide a stack region if necessary.
"""

from typing import Dict, Any, List, Optional
from . import assembler, emitter, alp_spec, stack_model
from .emitter import read_word, write_word, resolve_effective_address, operand_to_value
from .alp_spec import WORD_BYTES, DEFAULT_STACK_TOP_MULTIPLIER
import copy

def _make_initial_state(assembled: Dict[str, Any]) -> Dict[str, Any]:
    mem: bytearray = assembled.get("memory", bytearray())
    symbols: Dict[str,int] = dict(assembled.get("symbols", {}))

    # Ensure memory has some stack room: if small, extend by 4096 bytes (safe default)
    min_total = max(len(mem), 4096)
    if len(mem) < min_total:
        mem.extend([0] * (min_total - len(mem)))

    # Set initial registers
    regs = { f"R{i}": 0 for i in range(8) }
    # SP start near top of memory (word-aligned)
    sp = len(mem) - WORD_BYTES
    regs.update({"SP": sp, "FP": sp, "PC": None, "FLAGS": {"Z":0, "S":0}})
    state = {
        "registers": regs,
        "memory": mem,
        "symbols": symbols,
        # last written register name (used to interpret BRANCH >0 shorthand)
        "last_written_reg": None
    }
    return state

def _addr_of_label_operand(op: Dict[str,Any], symbols: Dict[str,int]) -> Optional[int]:
    """Return numeric address for a label-style operand (label name or operand.value)"""
    if not op:
        return None
    if op.get("mode") == "label":
        if "value" in op and op["value"] is not None:
            return int(op["value"])
        name = op.get("name")
        if name in symbols:
            return int(symbols[name])
        return None
    # if op is immediate with label
    if op.get("mode") == "immediate_label":
        if "value" in op and op["value"] is not None:
            return int(op["value"])
        name = op.get("name")
        if name in symbols:
            return int(symbols[name])
    return None

def simulate(assembled: Dict[str,Any], run_opts: Dict[str,Any]={}) -> Dict[str,Any]:
    """
    Execute assembled ALP program and emit event list.

    run_opts keys:
      - max_steps: int (safeguard)
      - step_limit: int (max events to return; if exceeded, events are truncated and truncated=True in result)
    """
    events: List[Dict[str,Any]] = []
    errors: List[str] = []
    truncated = False

    instructions: List[Dict] = assembled.get("instructions", [])
    # Build instruction map: addr -> inst
    inst_map: Dict[int, Dict] = { inst["addr"]: inst for inst in instructions }
    if not instructions:
        errors.append("No instructions to execute.")
        return {"events":[], "final_state": None, "errors": errors}

    # Setup state
    state = _make_initial_state(assembled)
    mem = state["memory"]
    regs = state["registers"]
    symbols = state["symbols"]

    # Decide initial PC: smallest instruction addr
    start_addr = min(inst_map.keys())
    regs["PC"] = start_addr

    max_steps = int(run_opts.get("max_steps", 200000))
    step_limit = int(run_opts.get("step_limit", 200000))
    step_count = 0
    event_id = 0

    def emit(evt_type: str, description: str, data: Dict[str,Any]):
        nonlocal event_id, events, step_limit, truncated
        event_id += 1
        evt = {
            "id": event_id,
            "type": evt_type,
            "time": step_count,
            "instr_addr": regs.get("PC"),
            "description": description,
            "data": data
        }
        events.append(evt)
        if len(events) >= step_limit:
            truncated = True
            # Stop collecting further events (but continue execution to avoid deadlocks? we'll stop execution)
            raise RuntimeError("Event limit reached; truncating")

    def push_word(value: int, what: str="word"):
        """Push a 4-byte word onto stack (decrement SP then write)."""
        nonlocal regs, mem
        sp_before = regs["SP"]
        new_sp = int(sp_before) - WORD_BYTES
        if new_sp < 0:
            raise RuntimeError("Stack overflow")
        regs["SP"] = new_sp
        write_word(mem, new_sp, value)
        # emit push event
        emit("push", f"push {what} -> addr {new_sp}", {"addr": new_sp, "value": value, "what": what})
        # also emit register update for SP
        emit("reg_update", f"SP <- {new_sp}", {"reg":"SP","old":sp_before,"new":new_sp})

    def pop_word(what: str="word") -> int:
        """Pop a 4-byte word from stack (read then increment SP)."""
        nonlocal regs, mem
        sp_before = regs["SP"]
        if sp_before + WORD_BYTES > len(mem):
            raise RuntimeError("Stack underflow")
        val = read_word(mem, sp_before)
        # emit pop event (value & addr)
        emit("pop", f"pop {what} <- addr {sp_before} value {val}", {"addr": sp_before, "value": val, "what": what})
        new_sp = sp_before + WORD_BYTES
        regs["SP"] = new_sp
        emit("reg_update", f"SP <- {new_sp}", {"reg":"SP","old":sp_before,"new":new_sp})
        return val

    # Execution loop
    try:
        while step_count < max_steps:
            step_count += 1
            pc = int(regs.get("PC"))
            if pc not in inst_map:
                # No instruction at PC -> stop execution
                emit("instruction", f"PC {pc} has no instruction. Halting.", {"addr": pc})
                break
            inst = inst_map[pc]
            mnemonic = inst.get("mnemonic", "").upper()
            operands = inst.get("operands", [])
            src_line = inst.get("source", "")
            # emit instruction event
            emit("instruction", f"Execute {mnemonic} {operands}", {"addr": pc, "mnemonic": mnemonic, "operands": operands, "source": src_line})

            # default next PC (advance) - some ops will change PC explicitly
            next_pc = pc + WORD_BYTES

            # helpers for resolving operands
            def _get_operand_val(op):
                return operand_to_value(op, state)

            def _write_to_operand(dst_op, value):
                # For register destination
                mode = dst_op.get("mode")
                if mode == "reg":
                    regname = dst_op["name"].upper()
                    old = regs.get(regname, 0)
                    regs[regname] = int(value & 0xFFFFFFFF)
                    state["last_written_reg"] = regname
                    emit("reg_update", f"{regname} <- {value}", {"reg":regname,"old":old,"new":regs[regname]})
                    return
                # For label destination: treat as memory at label address
                if mode in ("label","immediate_label"):
                    addr = _addr_of_label_operand(dst_op, symbols)
                    if addr is None:
                        raise RuntimeError("Undefined label for destination")
                    write_word(mem, addr, value)
                    emit("mem_write", f"WRITE mem[{addr}] <- {value}", {"addr":addr,"size":WORD_BYTES,"value":value})
                    return
                # For memory addressing
                addr = resolve_effective_address(dst_op, state)
                if addr is None:
                    raise RuntimeError(f"Destination operand not addressable: {dst_op}")
                write_word(mem, addr, value)
                emit("mem_write", f"WRITE mem[{addr}] <- {value}", {"addr":addr,"size":WORD_BYTES,"value":value})

            # Implement instructions
            if mnemonic == "MOVE":
                if len(operands) != 2:
                    raise RuntimeError("MOVE expects 2 operands")
                src_op = operands[0]
                dst_op = operands[1]
                val = _get_operand_val(src_op)
                _write_to_operand(dst_op, val)

            elif mnemonic in ("ADD",):
                if len(operands) != 2:
                    raise RuntimeError("ADD expects 2 operands")
                src_op = operands[0]
                dst_op = operands[1]
                src_val = _get_operand_val(src_op)
                # read current dst value
                # if dst is reg -> get current value
                if dst_op.get("mode") == "reg":
                    dst_reg = dst_op["name"].upper()
                    cur = regs.get(dst_reg, 0)
                else:
                    # memory dest: compute address and read
                    addr = resolve_effective_address(dst_op, state)
                    if addr is None:
                        raise RuntimeError("ADD: destination not addressable")
                    cur = read_word(mem, addr)
                    emit("mem_read", f"READ mem[{addr}] -> {cur}", {"addr":addr,"size":WORD_BYTES,"value":cur})
                newv = (int(cur) + int(src_val)) & 0xFFFFFFFF
                _write_to_operand(dst_op, newv)

            elif mnemonic in ("SUB",):
                if len(operands) != 2:
                    raise RuntimeError("SUB expects 2 operands")
                src_val = _get_operand_val(operands[0])
                dst_op = operands[1]
                if dst_op.get("mode") == "reg":
                    dst_reg = dst_op["name"].upper()
                    cur = regs.get(dst_reg, 0)
                else:
                    addr = resolve_effective_address(dst_op, state)
                    if addr is None:
                        raise RuntimeError("SUB: destination not addressable")
                    cur = read_word(mem, addr)
                    emit("mem_read", f"READ mem[{addr}] -> {cur}", {"addr":addr,"size":WORD_BYTES,"value":cur})
                newv = (int(cur) - int(src_val)) & 0xFFFFFFFF
                _write_to_operand(dst_op, newv)

            elif mnemonic in ("DECREMENT", "INCREMENT"):
                # map to ADD #1 / ADD #-1
                if len(operands) != 1:
                    raise RuntimeError(f"{mnemonic} expects 1 operand")
                op = operands[0]
                delta = -1 if mnemonic == "DECREMENT" else 1
                # construct a temp immediate operand
                cur_val = None
                if op.get("mode") == "reg":
                    cur_val = int(regs.get(op["name"].upper(), 0))
                else:
                    addr = resolve_effective_address(op, state)
                    if addr is None:
                        raise RuntimeError(f"{mnemonic}: operand not addressable")
                    cur_val = read_word(mem, addr)
                    emit("mem_read", f"READ mem[{addr}] -> {cur_val}", {"addr":addr,"size":WORD_BYTES,"value":cur_val})
                newv = (int(cur_val) + delta) & 0xFFFFFFFF
                _write_to_operand(op, newv)

            elif mnemonic in ("COMPARE",):
                if len(operands) != 2:
                    raise RuntimeError("COMPARE expects 2 operands")
                lhs = _get_operand_val(operands[0])
                rhs = _get_operand_val(operands[1])
                diff = int(lhs) - int(rhs)
                # Set flags
                flags = regs.get("FLAGS", {"Z":0,"S":0})
                flags["Z"] = 1 if diff == 0 else 0
                flags["S"] = 1 if diff > 0 else (-1 if diff < 0 else 0)
                regs["FLAGS"] = flags
                emit("compare", f"COMPARE {lhs} vs {rhs}", {"lhs":lhs,"rhs":rhs,"flags":flags})

            elif mnemonic in ("BRANCH", "BGT", "BLT", "BEQ", "BNE"):
                # Several forms:
                # BRANCH LABEL           -> unconditional
                # BRANCH >0, LABEL      -> shorthand (check last_written_reg >0)
                # BGT LABEL (use FLAGS)
                # We'll support the BRANCH cond, LABEL where cond may be unknown token with '>0'/'<0'/ '=0'
                taken = False
                target_addr = None
                cond_desc = None
                if mnemonic == "BRANCH":
                    if len(operands) == 1:
                        # unconditional to single label operand
                        target_addr = _addr_of_label_operand(operands[0], symbols)
                        taken = True
                    elif len(operands) == 2:
                        cond_op = operands[0]
                        tgt_op = operands[1]
                        # cond_op may be unknown token like '>0'
                        if cond_op.get("mode") == "unknown" and "token" in cond_op:
                            token = cond_op["token"].strip()
                            last_reg = state.get("last_written_reg")
                            if last_reg is not None:
                                val = int(regs.get(last_reg, 0))
                                if token in (">0", " >0"):
                                    taken = val > 0
                                elif token in ("<0"," <0"):
                                    taken = val < 0
                                elif token in ("=0","==0"," =0"):
                                    taken = val == 0
                                elif token in (">=0", ">= 0"):
                                    taken = val >= 0
                                else:
                                    # unknown condition default false
                                    taken = False
                                cond_desc = f"{last_reg} {token}"
                            else:
                                # fallback to FLAGS if no last_written_reg
                                flags = regs.get("FLAGS", {})
                                if token in (">0",):
                                    taken = flags.get("S",0) > 0
                                elif token in ("=0","==0"):
                                    taken = flags.get("Z",0) == 1
                                else:
                                    taken = False
                                cond_desc = f"FLAGS {token}"
                        else:
                            # cond_op could be a register or comparison result; try to resolve boolean
                            try:
                                v = _get_operand_val(cond_op)
                                taken = bool(v)
                                cond_desc = f"operand {v}"
                            except Exception:
                                taken = False
                        target_addr = _addr_of_label_operand(tgt_op, symbols)
                    else:
                        raise RuntimeError("BRANCH expects 1 or 2 operands")
                else:
                    # BGT/BLT/BEQ/BNE use FLAGS
                    if len(operands) != 1:
                        raise RuntimeError(f"{mnemonic} expects 1 operand")
                    target_addr = _addr_of_label_operand(operands[0], symbols)
                    flags = regs.get("FLAGS", {})
                    if mnemonic == "BGT":
                        taken = flags.get("S",0) > 0
                    elif mnemonic == "BLT":
                        taken = flags.get("S",0) < 0
                    elif mnemonic == "BEQ":
                        taken = flags.get("Z",0) == 1
                    elif mnemonic == "BNE":
                        taken = flags.get("Z",0) == 0
                emit("branch", f"BRANCH evaluate cond={cond_desc} taken={taken} -> {target_addr}", {"cond":cond_desc,"taken":taken,"target":target_addr})
                if taken:
                    if target_addr is None:
                        raise RuntimeError("BRANCH target address unresolved")
                    next_pc = int(target_addr)

            elif mnemonic in ("CALL",):
                # CALL LABEL
                if len(operands) != 1:
                    raise RuntimeError("CALL expects 1 operand")
                tgt_op = operands[0]
                target_addr = _addr_of_label_operand(tgt_op, symbols)
                if target_addr is None:
                    raise RuntimeError("CALL target unresolved")
                # Push return address (address of next instruction)
                ret_addr = pc + WORD_BYTES
                stack_model.push_return_address(state, ret_addr, emit=emit)
                stack_model.push_saved_fp(state, emit=emit)
                stack_model.set_frame_pointer(state, emit=emit)
                # emit push_frame summary:
                emit("push_frame", f"frame for call at {target_addr} created", {"func": target_addr, "start_addr": state['registers']['SP'], "size": WORD_BYTES * 2, "slots":[ {"name":"RET","addr": state['registers']['SP']+WORD_BYTES},{"name":"OLD_FP","addr": state['registers']['SP']}]})
                # jump to callee
                next_pc = int(target_addr)
            elif mnemonic in ("RETURN","RET"):
                # Restore frame using stack_model helper
                ret = stack_model.pop_frame(state, emit=emit)
                # stack_model.pop_frame will emit pop/reg_update/return events and returns ret address
                next_pc = int(ret)
                emit("return", f"RETURN to {ret}", {"from": pc, "to": ret})

            elif mnemonic in ("MOVEM",):
                # Two canonical forms in our subset:
                # MOVEM R0-R2, -(SP)  -> push R0,R1,R2 in ascending order onto stack (pre-decrement)
                # MOVEM (SP)+, R0-R2  -> pop into R0,R1,R2
                # We will parse operands token strings by looking at op dicts
                if len(operands) != 2:
                    raise RuntimeError("MOVEM expects 2 operands")
                left = operands[0]
                right = operands[1]
                # detect register list pattern as string in assembler._parse fallback; if mode unknown and token contains '-'
                def _expand_reglist(op):
                    # op could be dict with mode unknown and token like "R0-R2" or list encoded as label; implement simple parse
                    if op.get("mode") == "unknown" and "token" in op:
                        tok = op["token"].upper()
                        if "-" in tok:
                            a,b = tok.split("-",1)
                            a = a.strip()
                            b = b.strip()
                            # assume registers like R0..R7
                            ra = int(a.replace("R",""))
                            rb = int(b.replace("R",""))
                            return [f"R{i}" for i in range(ra, rb+1)]
                    # otherwise if mode == 'reg' and name contains comma (rare), attempt split
                    if op.get("mode") == "reg":
                        nm = op.get("name")
                        if "," in nm:
                            return [p.strip().upper() for p in nm.split(",")]
                        return [nm.upper()]
                    return []
                # Determine direction: if right is autodec -(SP), we push; if left is autodec -(SP) push
                if left.get("mode") == "unknown" and right.get("mode") == "autodec":
                    # push registers (left list) onto stack in order
                    reglist = _expand_reglist(left)
                    for r in reglist:
                        push_word(int(regs.get(r,0)), what=f"reg_{r}")
                elif left.get("mode") == "autodec":
                    # common other form: MOVEM (SP)+, R0-R2 is a pop sequence
                    # For simplicity, support right reglist form
                    reglist = _expand_reglist(right)
                    for r in reglist:
                        val = pop_word(what=f"reg_{r}")
                        old = regs.get(r,0)
                        regs[r] = val
                        emit("reg_update", f"{r} <- {val}", {"reg":r,"old":old,"new":val})
                else:
                    # fallback: not implemented
                    raise RuntimeError("MOVEM form not supported by this interpreter instance")

            else:
                # Unhandled instruction - for pedagogical subset, we allow unknowns but raise error
                raise RuntimeError(f"Unhandled instruction mnemonic: {mnemonic}")

            # advance PC
            regs["PC"] = int(next_pc)

    except RuntimeError as e:
        # If event limit reached we catch it but still return trimmed events
        if str(e).startswith("Event limit reached"):
            truncated = True
        else:
            errors.append(str(e))

    final_state = {
        "registers": copy.deepcopy(regs),
        "memory": mem,
        "symbols": symbols
    }
    result = {
        "events": events if not truncated else events,
        "final_state": final_state,
        "errors": errors
    }
    return result
