import sys

trace_log = []

def trace_func(frame, event, arg):
    func_name = frame.f_code.co_name

    # Ignore Python internals
    if func_name.startswith("<"):
        return trace_func

    if event == "call":
        trace_log.append({
            "event": "call",
            "function": func_name,
            "locals": dict(frame.f_locals)
        })
    elif event == "return":
        trace_log.append({
            "event": "return",
            "function": func_name,
            "return_value": arg
        })
    return trace_func


def run_and_trace(code):
    global trace_log
    trace_log = []

    try:
        sys.settrace(trace_func)
        exec(code, {})
        sys.settrace(None)
    except Exception as e:
        sys.settrace(None)
        return {"error": str(e)}

    return trace_log
