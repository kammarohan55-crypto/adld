import requests
import json

source = """ORIGIN 100
MOVE N,R1
END"""

r = requests.post('http://127.0.0.1:5000/simulate', json={'source': source})
result = r.json()

events = result.get('events', [])
print(f"Total events: {len(events)}")
print(f"\nEvent types: {sorted(set([e['type'] for e in events]))}")
print("\n--- First 3 Events ---")
for i in range(min(3, len(events))):
    e = events[i]
    print(f"\nEvent {i+1}:")
    print(f"  id: {e.get('id')}")
    print(f"  type: {e.get('type')}")
    print(f"  description: {e.get('description')}")
    print(f"  data keys: {list(e.get('data', {}).keys())}")
