# ALP Visualizer

A teaching-focused Assembly-Like Program (ALP) visualizer for pedagogical assembly language instruction.

## Features

- **Two-Pass Assembler**: Supports labels, directives (ORIGIN, DATAWORD, RESERVE, END), and all addressing modes
- **Instruction Set**: MOVE, ADD, SUB, MUL, DIV, COMPARE, BRANCH, CALL, RETURN, MOVEM, plus pseudo-instructions (PUSH, POP, CLR, INCREMENT, DECREMENT)
- **Micro-Operation Events**: Fine-grained event emission for every atomic operation (register updates, memory access, stack operations)
- **Interactive Visualization**: Real-time display of registers, memory, stack frames, and execution events
- **Pedagogical Focus**: Designed for teaching stack mechanics, subroutine calls, and assembly programming concepts

## Running the Visualizer

1. **Start the Flask server:**
   ```bash
   cd backend
   python app.py
   ```

2. **Open your browser** to `http://localhost:5000`

3. **Select "ALP Visualizer"** from the menu

4. **Enter ALP code** in the editor or click "Load Sample" to try the Sum-N example

5. **Click "Assemble"** to assemble your code, then **"Run"** to execute and visualize

## Example Program (Sum-N)

```assembly
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
```

This program:
- Loads count (5) into R1
- Points R2 to array NUM1
- Loops through array, adding values to R0
- Stores final sum (43) to memory location SUM

## Running Tests

```bash
cd backend
python tests/test_assembler.py
python tests/test_engine_alp_sum.py
python tests/test_nested_alp.py
```

## Architecture

### Backend Components

- **assembler.py**: Two-pass assembler with symbol table generation
- **engine_alp.py**: ALP interpreter with event emission
- **app.py**: Flask API endpoints (/assemble, /simulate)

### Frontend Components

- **templates/alp.html**: UI layout with editor, controls, and visualizations
- **static/alp_ui.js**: JavaScript event processor and visualization controller

### Event System

The engine emits fine-grained events for:
- `instruction`: Instruction fetch/decode
- `reg_update`: Register modifications
- `mem_read`/`mem_write`: Memory access
- `push`/`pop`: Stack operations
- `push_frame`/`pop_frame`: Stack frame creation/destruction
- `call`/`return`: Subroutine control flow
- `compare`: Comparison and flag updates
- `branch`: Branch decisions
- `error`: Runtime errors

## Addressing Modes

- **Immediate**: `#42` or `#LABEL`
- **Register**: `R0`, `R1`, ..., `SP`, `FP`, `PC`
- **Indirect**: `(R2)` - address in R2
- **Auto-decrement**: `-(R2)` - decrement then use
- **Auto-increment**: `(R2)+` - use then increment
- **Indexed**: `12(R0)` - R0 + 12
- **Direct**: `LABEL` - direct memory address

## Stack Frame Layout (CALL/RETURN)

```
Higher addresses
  <caller params>
  return address    ← PC after CALL
  savedFP           ← old FP value
  saved registers   ← callee-saved (MOVEM)
  locals            ← local variables
Lower addresses (SP points here)
```

## Contributing

The ALP visualizer is designed for educational use. Feel free to extend the instruction set, add more examples, or enhance the visualization.

## License

MIT