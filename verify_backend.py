import requests
import json
import traceback

BASE_URL = "http://127.0.0.1:5000"

SUM_N_ITERATIVE = """ORIGIN 100
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

# Sum-N Recursive to test stack
# int sum_n(int n, int* arr) {
#   if (n <= 0) return 0;
#   return *arr + sum_n(n-1, arr+1);
# }
# Wait, let's keep it simpler for stack test: just nested calls
NESTED_CALLS = """ORIGIN 100
CALL SUB1
; Engine stops when no instruction at PC
ORIGIN 200
SUB1:
  CALL SUB2
  RETURN
SUB2:
  MOVE #123, R0
  MOVE R0, RESULT
  RETURN
ORIGIN 300
RESULT: RESERVE 4
END"""

def run_test(name, source):
    print(f"--- Running {name} ---")
    try:
        r = requests.post(f"{BASE_URL}/simulate", json={"source": source})
        r.raise_for_status()
        res = r.json()
        if res.get("errors"):
            print(f"Errors: {res['errors']}")
            return events if 'events' in locals() else []
        
        events = res.get("events", [])
        print(f"Total events: {len(events)}")
        
        types = set(e["type"] for e in events)
        print(f"Event types found: {sorted(list(types))}")
        
        required = {"instruction", "reg_update", "mem_write", "push", "pop", "push_frame"}
        missing = required - types
        
        if missing:
            print(f"MISSING types: {missing}")
        else:
            print("ALL required types found!")
            
        if events:
            print("First event sample:")
            print(json.dumps(events[0], indent=2))
            # Also notify on missing instrumentation if important ones are missing but expected
            
        return events

    except Exception:
        traceback.print_exc()
        return []

if __name__ == "__main__":
    print("Verifying backend with samples...")
    print("\n")
    events_iter = run_test("Sum-N (Iterative)", SUM_N_ITERATIVE)
    print("\n")
    events_stack = run_test("Nested Calls (Stack Test)", NESTED_CALLS)

