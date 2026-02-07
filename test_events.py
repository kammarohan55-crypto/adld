import requests
import json

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

r = requests.post('http://127.0.0.1:5000/simulate', json={'source': source})
result = r.json()

events = result.get('events', [])
print(f"Total events: {len(events)}\n")

# Get unique event types
event_types = sorted(set([e['type'] for e in events]))
print(f"Event types found: {event_types}\n")

# Print first 5 events with full details
print("First 5 events:\n")
for i, event in enumerate(events[:5]):
    print(f"Event {i+1}:")
    print(json.dumps(event,indent=2))
    print()
