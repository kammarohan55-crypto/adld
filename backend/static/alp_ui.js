// backend/static/alp_ui.js
document.addEventListener("DOMContentLoaded", function () {
    const srcArea = document.getElementById("editor");
    const assembleBtn = document.getElementById("assembleBtn");
    const runBtn = document.getElementById("runBtn");
    const eventsDiv = document.getElementById("eventLog");
    const symbolsDiv = document.getElementById("symbols");
    const stepBtn = document.getElementById("stepBtn");
    const stepOverBtn = document.getElementById("stepOverBtn");
    const resetBtn = document.getElementById("resetBtn"); // Ensure reset button is also selected if not already

    let simulationEvents = [];
    let eventIndex = 0;

    function updateButtons() {
        const hasEvents = simulationEvents.length > 0;
        const canStep = eventIndex < simulationEvents.length;
        stepBtn.disabled = !hasEvents || !canStep;
        stepOverBtn.disabled = !hasEvents || !canStep;
    }

    function renderEvent(evt) {
        const p = document.createElement("pre");
        // Simple formatting
        let info = "";
        if (evt.type === "instruction") info = `${evt.data.mnemonic} ${evt.data.operands ? JSON.stringify(evt.data.operands) : ""}`;
        else if (evt.type === "reg_update") info = `${evt.data.reg} <- ${evt.data.new}`;
        else if (evt.type === "mem_write") info = `[${evt.data.addr}] <- ${evt.data.value}`;
        else if (evt.type === "push") info = `PUSH ${evt.data.value} -> [${evt.data.addr}]`;
        else if (evt.type === "pop") info = `POP ${evt.data.value} <- [${evt.data.addr}]`;
        else info = JSON.stringify(evt.data);

        p.textContent = `[${evt.id}] ${evt.type} ${evt.description}`;
        p.className = "event-item";
        eventsDiv.appendChild(p);
        eventsDiv.scrollTop = eventsDiv.scrollHeight;

        // Visual updates can go here if we parsed them (e.g. highlight register)
    }

    assembleBtn.addEventListener("click", async () => {
        const source = srcArea.value;
        const res = await fetch("/assemble", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source }) });
        const j = await res.json();
        symbolsDiv.innerText = JSON.stringify(j.symbols, null, 2);
        if (j.errors && j.errors.length) alert("Assemble errors:\n" + j.errors.join("\n"));
        else {
            runBtn.disabled = false;
        }
    });

    runBtn.addEventListener("click", async () => {
        eventsDiv.innerHTML = "";
        simulationEvents = [];
        eventIndex = 0;
        updateButtons();

        const source = srcArea.value;
        // Request a large step limit to get full stream
        const res = await fetch("/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source, run_opts: { step_limit: 100000 } }) });
        const j = await res.json();

        if (j.errors && j.errors.length) {
            alert("Runtime errors:\n" + j.errors.join("\n"));
            return;
        }

        simulationEvents = j.events || [];
        if (simulationEvents.length === 0) {
            eventsDiv.innerHTML = "No events generated.";
            return;
        }

        // Check for truncation (if backend supported returning a truncated flag, we'd check it. 
        // For now, if we hit 100000, we might assume truncation or just not worry)
        // If the last event ID is high, it likely worked. Be simple.

        // Enable step buttons
        stepBtn.disabled = false;
        stepOverBtn.disabled = false;

        // Auto-scroll to top of log
        eventsDiv.innerHTML = "<em>Simulation loaded. Use Step/Step Over or see below.</em><br/>";
    });

    stepBtn.addEventListener("click", () => {
        if (eventIndex < simulationEvents.length) {
            renderEvent(simulationEvents[eventIndex]);
            eventIndex++;
            updateButtons();
        }
    });

    stepOverBtn.addEventListener("click", () => {
        if (eventIndex >= simulationEvents.length) return;

        const startEvt = simulationEvents[eventIndex];
        // If it is a CALL instruction, we want to step until we return from it.
        // Heuristic:
        // 1. If not CALL, just step 1.
        // 2. If CALL, scan ahead for matching return? 
        //    Actually, simple heuristic: Count "push_frame" vs "return" or better:
        //    Since we have a flat event stream, we can just look for the return event that corresponds to this call?
        //    No, "return" event doesn't link to "call" ID directly in current schema easily without parsing.
        //    Better heuristic: 
        //      Depth counter: start=0. 
        //      Iterate:
        //        current = events[i]
        //        if current is CALL (instruction mnemonic CALL), depth++
        //        if current is RETURN (instruction mnemonic RETURN/RET or type 'return'?), depth--
        //      Stop when depth == 0 and we are past the start index.

        // Let's refine:
        // The event stream has "instruction" events and "push_frame"/"return" events.
        // Only "instruction" events move the PC in a major way we care about for "Step Over" at source level.
        // BUT "push_frame" happens *inside* the CALL instruction execution usually?
        // No, `simulate` returns a trace.
        // Event[i] = instruction CALL
        // Event[i+1] = push_frame (emitted by CALL)
        // Event[i+2] = instruction (first instr of callee)
        // ...
        // Event[k] = instruction RETURN
        // Event[k+1] = return (event)

        // So if we are at `instruction` and mnemonic is `CALL`:
        //   Target depth = 0.
        //   We are 'into' the call.
        //   Scan forward.
        //   Count `push_frame` (depth++) and `return` (depth--).
        //   Wait, the `CALL` instruction itself emits `push_frame` immediately after.
        //   So we are at `CALL`.
        //   Render it.
        //   Then loop: render next events.
        //   If we see `push_frame`, depth++.
        //   If we see `return` event, depth--.
        //   Stop when depth == 0.

        // Logic:
        // 1. Render current event.
        // 2. If it was NOT a CALL instruction, done.
        // 3. If it WAS a CALL, enter loop:
        //      While hasNext:
        //         Peek next event.
        //         Render it.
        //         If event.type === 'push_frame', depth++.
        //         If event.type === 'return', depth--.
        //         If depth == 0: break.

        // Wait, initial CALL instruction doesn't increase depth? 
        // The `push_frame` event does.
        // So:
        //   Execute current event (the CALL instruction). 
        //   (It might trigger a push_frame next? No, simulate returns linear list).
        //   Yes, `CALL` emits `push_frame`.
        //   So after rendering CALL instruction (evt i), the next event (i+1) is `push_frame`?
        //   Let's check engine.
        //   Engine `CALL`: emit "push_frame", then done. 
        //   Next instruction event is the target.
        //   So: 
        //   Evt[0]: Instruction CALL
        //   Evt[1]: push_frame
        //   Evt[2]: Instruction (callee start)

        //   So if I am at Evt[0] (CALL):
        //     Render Evt[0].
        //     Is it CALL? Yes.
        //     Loop:
        //       Render Evt[1] (push_frame). Depth becomes 1 (0->1).
        //       Render Evt[2] (instr).
        //       ...
        //       Render Evt[k] (return). Depth becomes 0 (1->0).
        //       Break.
        //   This seems correct.

        const isCall = (startEvt.type === "instruction" && startEvt.data.mnemonic === "CALL");

        // Always render the current one
        renderEvent(startEvt);
        eventIndex++;

        if (isCall) {
            let depth = 0;
            // Scan forward
            while (eventIndex < simulationEvents.length) {
                const evt = simulationEvents[eventIndex];
                renderEvent(evt);
                eventIndex++;

                if (evt.type === "push_frame") {
                    depth++;
                } else if (evt.type === "return") {
                    depth--;
                    // If we returned to depth 0, we are done with this call
                    if (depth <= 0) break;
                }
            }
        }
        updateButtons();
    });

    const loadSampleBtn = document.getElementById("loadSampleBtn");
    loadSampleBtn.addEventListener("click", () => {
        const sampleCode = `ORIGIN 100
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
END`;
        srcArea.value = sampleCode;
    });
});
