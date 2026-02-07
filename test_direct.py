import backend.assembler as assembler
import backend.engine_alp as engine_alp

# Sum-N program
source = """ORIGIN 100
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
END"""

print("=== Testing ALP Assembler & Simulator ===\n")

# Assemble
assembled = assembler.assemble(source)
print(f"Assembly errors: {assembled.get('errors', [])}")
print(f"Symbols: {list(assembled.get('symbols', {}).keys())}")

# Simulate
result = engine_alp.simulate(assembled, run_opts={"max_steps": 10000})
events = result.get('events', [])

print(f"\nTotal events emitted: {len(events)}")

# Get unique event types
event_types = sorted(set([e['type'] for e in events]))
print(f"\nEvent types found:")
for t in event_types:
    print(f"  - {t}")

# Print first 5 events
print("\n=== First 5 Events ===\n")
for i, e in enumerate(events[:5]):
    print(f"Event {i+1}:")
    print(f"  ID: {e.get('id')}")
    print(f"  Type: {e.get('type')}")
    print(f"  Description: {e.get('description')}")
    print(f"  Data keys: {list(e.get('data', {}).keys())}")
    print()

# Example full event
print("\n=== Example Event (Event 1) ===")
import json
print(json.dumps(events[0], indent=2))
