"""
Unit test for ALP engine using the Sum-N example program.
Validates correct execution and final result.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from assembler import assemble
from engine_alp import simulate


# Sum-N program from specification
SUM_N_PROGRAM = """
ORIGIN 100
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


def test_sum_n_assembly():
    """Test that Sum-N program assembles correctly."""
    result = assemble(SUM_N_PROGRAM)
    
    assert result['success'], f"Assembly failed: {result['errors']}"
    assert 'SUM' in result['symbols']
    assert 'N' in result['symbols']
    assert 'NUM1' in result['symbols']
    assert 'LOOP' in result['symbols']
    
    # Check symbol addresses
    assert result['symbols']['SUM'] == 200
    assert result['symbols']['N'] == 204
    assert result['symbols']['NUM1'] == 208
    
    # Check data memory initialization
    assert result['data_memory'][204] == 5  # N
    assert result['data_memory'][208] == 2  # NUM1[0]
    assert result['data_memory'][212] == 5  # NUM1[1]
    assert result['data_memory'][216] == 7  # NUM1[2]
    assert result['data_memory'][220] == -1  # NUM1[3]
    assert result['data_memory'][224] == 30  # NUM1[4]
    
    print("✓ Assembly validation passed")
    return result


def test_sum_n_execution():
    """Test that Sum-N program executes correctly and produces expected result."""
    result = assemble(SUM_N_PROGRAM)
    assert result['success']
    
    # Simulate execution
    events = simulate(result)
    
    # Check that we got events
    assert len(events) > 0, "No events generated"
    
    # Find final register and memory state from events
    final_r0 = None
    final_r1 = None
    final_r2 = None
    final_sum = None
    
    for event in events:
        if event['type'] == 'reg_update':
            if event['data']['reg'] == 'R0':
                final_r0 = event['data']['new']
            elif event['data']['reg'] == 'R1':
                final_r1 = event['data']['new']
            elif event['data']['reg'] == 'R2':
                final_r2 = event['data']['new']
        elif event['type'] == 'mem_write':
            if event['data']['addr'] == 200:  # SUM address
                final_sum = event['data']['value']
    
    # Expected sum: 2 + 5 + 7 + (-1) + 30 = 43
    assert final_r0 == 43, f"Expected R0=43, got R0={final_r0}"
    assert final_r1 == 0, f"Expected R1=0 (count down), got R1={final_r1}"
    assert final_sum == 43, f"Expected SUM=43, got SUM={final_sum}"
    
    print(f"✓ Execution validation passed: R0={final_r0}, SUM={final_sum}")
    

def test_event_types():
    """Test that all expected event types are generated."""
    result = assemble(SUM_N_PROGRAM)
    events = simulate(result)
    
    event_types = set(e['type'] for e in events)
    
    # Should have instruction, reg_update, mem_read, mem_write, branch events
    assert 'instruction' in event_types
    assert 'reg_update' in event_types
    assert 'mem_read' in event_types
    assert 'mem_write' in event_types
    assert 'branch' in event_types
    
    print(f"✓ Event types validation passed: {event_types}")


def test_loop_iterations():
    """Test that loop executes correct number of times."""
    result = assemble(SUM_N_PROGRAM)
    events = simulate(result)
    
    # Count branch decisions
    branch_events = [e for e in events if e['type'] == 'branch']
    
    # Should have N (5) taken branches + 1 not-taken branch
    taken = sum(1 for e in branch_events if e['data']['taken'])
    not_taken = sum(1 for e in branch_events if not e['data']['taken'])
    
    assert taken == 5, f"Expected 5 taken branches, got {taken}"
    assert not_taken == 1, f"Expected 1 not-taken branch, got {not_taken}"
    
    print(f"✓ Loop iteration validation passed: {taken} taken, {not_taken} not-taken")


if __name__ == '__main__':
    print("Running Sum-N program tests...\n")
    
    tests = [
        test_sum_n_assembly,
        test_sum_n_execution,
        test_event_types,
        test_loop_iterations
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
