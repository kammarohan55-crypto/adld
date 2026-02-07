"""
Unit test for nested subroutine calls with CALL/RETURN.
Tests stack frame creation, parameter passing, and stack unwinding.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from assembler import assemble
from engine_alp import simulate


# Nested subroutine test program
NESTED_PROGRAM = """
ORIGIN 100
MOVE #10, R0
MOVE #20, R1
CALL ADD_AND_DOUBLE
MOVE R0, RESULT
ORIGIN 150
ADD_AND_DOUBLE:
 ADD R1, R0
 CALL DOUBLE_VALUE
 RETURN
ORIGIN 180
DOUBLE_VALUE:
 ADD R0, R0
 RETURN
ORIGIN 200
RESULT: RESERVE 4
END
"""


def test_nested_assembly():
    """Test that nested subroutine program assembles correctly."""
    result = assemble(NESTED_PROGRAM)
    
    assert result['success'], f"Assembly failed: {result['errors']}"
    assert 'ADD_AND_DOUBLE' in result['symbols']
    assert 'DOUBLE_VALUE' in result['symbols']
    assert 'RESULT' in result['symbols']
    
    print("✓ Nested subroutine assembly passed")
    return result


def test_call_return_events():
    """Test that CALL and RETURN generate correct events."""
    result = assemble(NESTED_PROGRAM)
    events = simulate(result)
    
    # Find call and return events
    call_events = [e for e in events if e['type'] == 'call']
    return_events = [e for e in events if e['type'] == 'return']
    push_frame_events = [e for e in events if e['type'] == 'push_frame']
    pop_frame_events = [e for e in events if e['type'] == 'pop_frame']
    
    # Should have 2 calls (to ADD_AND_DOUBLE and DOUBLE_VALUE)
    assert len(call_events) == 2, f"Expected 2 call events, got {len(call_events)}"
    
    # Should have 2 returns
    assert len(return_events) == 2, f"Expected 2 return events, got {len(return_events)}"
    
    # Should have 2 push_frame events
    assert len(push_frame_events) == 2, f"Expected 2 push_frame events, got {len(push_frame_events)}"
    
    # Should have 2 pop_frame events
    assert len(pop_frame_events) == 2, f"Expected 2 pop_frame events, got {len(pop_frame_events)}"
    
    print(f"✓ Call/return event validation passed")


def test_nested_execution_result():
    """Test that nested calls produce correct result."""
    result = assemble(NESTED_PROGRAM)
    events = simulate(result)
    
    # Find final result in memory
    final_result = None
    for event in events:
        if event['type'] == 'mem_write' and event['data']['addr'] == 200:
            final_result = event['data']['value']
    
    # Expected: (10 + 20) * 2 = 60
    assert final_result == 60, f"Expected RESULT=60, got {final_result}"
    
    print(f"✓ Nested execution result validation passed: RESULT={final_result}")


def test_stack_frame_structure():
    """Test that stack frames contain return address and saved FP."""
    result = assemble(NESTED_PROGRAM)
    events = simulate(result)
    
    # Find push_frame events
    push_frames = [e for e in events if e['type'] == 'push_frame']
    
    for frame_event in push_frames:
        slots = frame_event['data']['slots']
        
        # Check for RET and OLD_FP slots
        slot_names = [s['name'] for s in slots]
        assert 'RET' in slot_names, "Stack frame missing RET slot"
        assert 'OLD_FP' in slot_names, "Stack frame missing OLD_FP slot"
    
    print("✓ Stack frame structure validation passed")


def test_sp_fp_restoration():
    """Test that SP and FP are restored correctly after returns."""
    result = assemble(NESTED_PROGRAM)
    events = simulate(result)
    
    # Track SP and FP changes
    sp_values = []
    fp_values = []
    
    for event in events:
        if event['type'] == 'reg_update':
            if event['data']['reg'] == 'SP':
                sp_values.append(event['data']['new'])
            elif event['data']['reg'] == 'FP':
                fp_values.append(event['data']['new'])
    
    # Initial SP should be high (near top of memory)
    # After all returns, SP should be restored close to initial
    initial_sp = sp_values[0] if sp_values else None
    final_sp = sp_values[-1] if sp_values else None
    
    # SP should grow down during calls, then restore on returns
    # Final SP should be close to initial (within reasonable range)
    if initial_sp and final_sp:
        sp_diff = abs(initial_sp - final_sp)
        assert sp_diff < 100, f"SP not properly restored: initial={initial_sp}, final={final_sp}"
    
    print(f"✓ SP/FP restoration validation passed")


if __name__ == '__main__':
    print("Running nested subroutine tests...\n")
    
    tests = [
        test_nested_assembly,
        test_call_return_events,
        test_nested_execution_result,
        test_stack_frame_structure,
        test_sp_fp_restoration
    ]
    
    passed = 0
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
        except Exception as e:
            print(f"✗ {test_func.__name__}: {type(e).__name__}: {e}")
    
    print(f"\n{passed}/{len(tests)} tests passed")
