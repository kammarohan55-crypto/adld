from . import tracer
from . import stack_model

def simulate(code):
    trace = tracer.run_and_trace(code)
    vs = stack_model.VirtualStack()
    timeline = []
    last_frame = None

    for e in trace:
        if e["event"] == "call":
            frame = vs.push_frame(e["function"], e["locals"])
            last_frame = frame
            # Only add the last non-main function frame to timeline
            if e["function"] != "main":
                timeline.append({
                    "type": "push",
                    "func": e["function"],
                    "slots": frame.slots
                })

        elif e["event"] == "return" and e["function"] != "main" and last_frame:
            # Add pop events for unwinding - Level 1 → Level 2 → Level 3
            for slot in last_frame.slots:
                timeline.append({
                    "type": "pop",
                    "func": e["function"],
                    "slot": slot
                })

    return timeline

