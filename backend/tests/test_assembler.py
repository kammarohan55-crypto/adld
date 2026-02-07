"""
Unit tests for ALP assembler.
Tests directive parsing, symbol table generation, and addressing modes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from assembler import assemble


def test_simple_directive():
    """Test ORIGIN and DATAWORD directives."""
    source = """
    ORIGIN 100
    DATAWORD 42
    END
    """
    result = assemble(source)
    assert result['success'], f"Assembly failed: {result['errors']}"
    assert 100 in result['data_memory']
    assert result['data_memory'][100] == 42


def test_labels():
    """Test label definition and symbol table."""
    source = """
    ORIGIN 200
    NUM: DATAWORD 123
    END
    """
    result = assemble(source)
    assert result['success']
    assert 'NUM' in result['symbols']
    assert result['symbols']['NUM'] == 200
    assert result['data_memory'][200] == 123


def test_reserve():
    """Test RESERVE directive."""
    source = """
    ORIGIN 300
    BUF: RESERVE 12
    END
    """
    result = assemble(source)
    assert result['success']
    assert 'BUF' in result['symbols']
    assert result['symbols']['BUF'] == 300
    # Should reserve 12 bytes (3 words)
    assert 300 in result['data_memory']
    assert 304 in result['data_memory']
    assert 308 in result['data_memory']


def test_move_instruction():
    """Test MOVE instruction parsing."""
    source = """
    ORIGIN 100
    MOVE R0, R1
    END
    """
    result = assemble(source)
    assert result['success']
    assert len(result['instructions']) == 1
    instr = result['instructions'][0]
    assert instr['mnemonic'] == 'MOVE'
    assert len(instr['operands']) == 2
    assert instr['operands'][0]['mode'] == 'register'
    assert instr['operands'][0]['reg'] == 'R0'


def test_addressing_modes():
    """Test all addressing modes."""
    source = """
    ORIGIN 100
    MOVE #42, R0
    MOVE R1, R2
    MOVE (R3), R4
    MOVE -(R5), R6
    MOVE (R7)+, R0
    MOVE 12(R1), R2
    END
    """
    result = assemble(source)
    assert result['success'], f"Errors: {result['errors']}"
    assert len(result['instructions']) == 6
    
    # Immediate
    assert result['instructions'][0]['operands'][0]['mode'] == 'immediate'
    assert result['instructions'][0]['operands'][0]['value'] == 42
    
    # Register
    assert result['instructions'][1]['operands'][0]['mode'] == 'register'
    
    # Indirect
    assert result['instructions'][2]['operands'][0]['mode'] == 'indirect'
    
    # Auto-decrement
    assert result['instructions'][3]['operands'][0]['mode'] == 'auto_dec'
    
    # Auto-increment
    assert result['instructions'][4]['operands'][0]['mode'] == 'auto_inc'
    
    # Indexed
    assert result['instructions'][5]['operands'][0]['mode'] == 'indexed'
    assert result['instructions'][5]['operands'][0]['offset'] == 12


def test_pseudo_instructions():
    """Test pseudo-instruction translation."""
    source = """
    ORIGIN 100
    PUSH R0
    POP R1
    CLR R2
    INCREMENT R3
    DECREMENT R4
    END
    """
    result = assemble(source)
    assert result['success']
    
    # PUSH -> MOVE R0, -(SP)
    assert result['instructions'][0]['mnemonic'] == 'MOVE'
    assert result['instructions'][0]['original_mnemonic'] == 'PUSH'
    
    # POP -> MOVE (SP)+, R1
    assert result['instructions'][1]['mnemonic'] == 'MOVE'
    assert result['instructions'][1]['original_mnemonic'] == 'POP'
    
    # CLR -> MOVE #0, R2
    assert result['instructions'][2]['mnemonic'] == 'MOVE'
    assert result['instructions'][2]['original_mnemonic'] == 'CLR'
    
    # INCREMENT -> ADD #1, R3
    assert result['instructions'][3]['mnemonic'] == 'ADD'
    assert result['instructions'][3]['original_mnemonic'] == 'INCREMENT'
    
    # DECREMENT -> ADD #-1, R4
    assert result['instructions'][4]['mnemonic'] == 'ADD'
    assert result['instructions'][4]['original_mnemonic'] == 'DECREMENT'


def test_branch_instruction():
    """Test BRANCH with conditions."""
    source = """
    ORIGIN 100
    LOOP: ADD R0, R1
    BRANCH >0, LOOP
    END
    """
    result = assemble(source)
    assert result['success']
    assert 'LOOP' in result['symbols']
    assert result['symbols']['LOOP'] == 100
    
    instr = result['instructions'][1]
    assert instr['mnemonic'] == 'BRANCH'
    assert instr['condition'] == '>0'


def test_call_return():
    """Test CALL and RETURN."""
    source = """
    ORIGIN 100
    CALL SUB1
    ORIGIN 200
    SUB1: ADD R0, R1
    RETURN
    END
    """
    result = assemble(source)
    assert result['success']
    assert 'SUB1' in result['symbols']
    assert result['symbols']['SUB1'] == 200
    
    assert result['instructions'][0]['mnemonic'] == 'CALL'
    assert result['instructions'][2]['mnemonic'] == 'RETURN'


def test_error_duplicate_label():
    """Test error on duplicate label."""
    source = """
    ORIGIN 100
    NUM: DATAWORD 1
    NUM: DATAWORD 2
    END
    """
    result = assemble(source)
    assert not result['success']
    assert len(result['errors']) > 0
    assert 'Duplicate' in result['errors'][0]


def test_multivalue_dataword():
    """Test DATAWORD with multiple values."""
    source = """
    ORIGIN 100
    ARRAY: DATAWORD 1,2,3,4,5
    END
    """
    result = assemble(source)
    assert result['success']
    assert 'ARRAY' in result['symbols']
    assert result['symbols']['ARRAY'] == 100
    assert result['data_memory'][100] == 1
    assert result['data_memory'][104] == 2
    assert result['data_memory'][108] == 3
    assert result['data_memory'][112] == 4
    assert result['data_memory'][116] == 5


if __name__ == '__main__':
    print("Running assembler tests...")
    
    tests = [
        test_simple_directive,
        test_labels,
        test_reserve,
        test_move_instruction,
        test_addressing_modes,
        test_pseudo_instructions,
        test_branch_instruction,
        test_call_return,
        test_error_duplicate_label,
        test_multivalue_dataword
    ]
    
    passed = 0
    for test_func in tests:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
        except Exception as e:
            print(f"✗ {test_func.__name__}: {type(e).__name__}: {e}")
    
    print(f"\n{passed}/{len(tests)} tests passed")
