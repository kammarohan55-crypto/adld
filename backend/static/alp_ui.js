// backend/static/alp_ui.js
// Enhanced ALP UI event consumer: registers, memory and simple stack visualization.
// Replaces previous lightweight implementation with live visual updates.
//
// Assumptions:
// - Server POST /assemble returns {"symbols": {...}, ...}
// - Server POST /simulate returns {"events":[...], "final_state_meta": {"registers": {...}, "memory_size": ...}, "errors": [...] }
// - Events follow the schema defined in the project and include types:
//   "instruction", "reg_update", "mem_write", "mem_read", "push", "pop", "branch", "push_frame", "return", "compare"
//
// Notes:
// - The script updates #registerGrid and #memoryBody (existing elements) and uses event log #eventLog.
// - Simple stack view is implemented from push/pop events (stackList). SP/FP shown in register grid.

console.log("alp_ui.js LOADED");
document.addEventListener("DOMContentLoaded", function () {
    const srcArea = document.getElementById("editor");
    const assembleBtn = document.getElementById("assembleBtn");
    const runBtn = document.getElementById("runBtn");
    const eventsDiv = document.getElementById("eventLog");
    const symbolsDiv = document.getElementById("symbols");
    const stepBtn = document.getElementById("stepBtn");
    const stepOverBtn = document.getElementById("stepOverBtn");
    const resetBtn = document.getElementById("resetBtn");
    const loadSampleBtn = document.getElementById("loadSampleBtn");
    const registerGrid = document.getElementById("registerGrid");
    const memoryBody = document.getElementById("memoryBody");

    // runtime state maintained in front-end
    let simulationEvents = [];
    let eventIndex = 0;
    let registers = {};   // map name -> value
    let memoryMap = {};   // addr -> value (32-bit)
    let stackList = [];   // array of {addr, value, what} representing pushes (top at index 0)
    let lastEventRendered = null;

    function resetFrontendState() {
        simulationEvents = [];
        eventIndex = 0;
        registers = {};
        memoryMap = {};
        stackList = [];
        eventsDiv.innerHTML = "";
        renderRegisterGrid();
        renderMemoryTable();
    }

    // Renderers
    function renderRegisterGrid() {
        // registers object may be sparse; show canonical registers order if present
        const order = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "SP", "FP", "PC", "FLAGS"];
        registerGrid.innerHTML = "";
        for (let r of order) {
            const val = registers.hasOwnProperty(r) ? registers[r] : "";
            const el = document.createElement("div");
            el.className = "register-item";
            el.innerHTML = `<div class="reg-name">${r}</div><div class="reg-value">${formatRegValue(val)}</div>`;
            registerGrid.appendChild(el);
        }
    }

    function formatRegValue(v) {
        if (v === null || v === undefined || v === "") return "";
        // special-case FLAGS object
        if (typeof v === "object" && v !== null) {
            try {
                return JSON.stringify(v);
            } catch (e) {
                return String(v);
            }
        }
        // show hex and decimal
        const num = Number(v) >>> 0; // treat as unsigned 32-bit
        return `0x${num.toString(16).padStart(8, "0")} (${num})`;
    }

    function renderMemoryTable() {
        // Show written memory addresses sorted descending (higher addresses first)
        memoryBody.innerHTML = "";
        const addrs = Object.keys(memoryMap).map(a => parseInt(a, 10)).sort((a, b) => b - a);
        // If no memoryMap entries, show a placeholder
        if (addrs.length === 0) {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td colspan="3" style="opacity:0.6;">(no memory writes yet)</td>`;
            memoryBody.appendChild(tr);
            return;
        }
        for (let addr of addrs) {
            const v = memoryMap[addr];
            const hex = "0x" + ((v >>> 0).toString(16).padStart(8, "0")).toUpperCase();
            const dec = (v >>> 0);
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${addr}</td><td>${hex}</td><td>${dec}</td>`;
            memoryBody.appendChild(tr);
        }
    }

    function renderEvent(evt) {
        const p = document.createElement("div");
        p.className = "event-row";
        p.textContent = `[${evt.id}] ${evt.type} ${evt.description}`;
        // show data as a small JSON blob
        const pre = document.createElement("pre");
        pre.className = "event-data";
        try { pre.textContent = JSON.stringify(evt.data, null, 2); } catch (e) { pre.textContent = String(evt.data); }
        p.appendChild(pre);
        eventsDiv.appendChild(p);
        eventsDiv.scrollTop = eventsDiv.scrollHeight;
    }

    // Event handling (updates registers/memory/stack)
    function handleEvent(evt) {
        // call before rendering so UI reflects new values in same tick
        const t = evt.type;
        if (t === "reg_update") {
            const d = evt.data || {};
            const r = d.reg;
            const nv = d.new;
            registers[r] = nv;
            // if SP/FP changed we want to reflect that and adjust stack visualization
            if (r === "SP") {
                // SP change does not itself reveal pushed value; we track pushes/pops separately from push/pop events
                // but we still update the display
            }
            renderRegisterGrid();
        } else if (t === "mem_write" || t === "mem_read") {
            const d = evt.data || {};
            const a = d.addr;
            const v = d.value;
            if (typeof a === "number") {
                memoryMap[a] = v >>> 0;
                renderMemoryTable();
            }
        } else if (t === "push") {
            // push contains addr and value and what
            const d = evt.data || {};
            const a = d.addr;
            const v = d.value;
            const what = d.what || "word";
            // treat top of stack as index 0
            stackList.unshift({ addr: a, value: (v >>> 0), what: what });
            // update memory map too
            memoryMap[a] = (v >>> 0);
            renderMemoryTable();
            renderStackSnapshot();
        } else if (t === "pop") {
            const d = evt.data || {};
            // popped address shown in event; remove first matching entry from stackList with same addr
            const a = d.addr;
            // remove first element matching addr (if exists)
            const idx = stackList.findIndex(s => s.addr === a);
            if (idx !== -1) stackList.splice(idx, 1);
            renderStackSnapshot();
        } else if (t === "push_frame") {
            // push_frame event contains start_addr and slots: use as summary
            // optional: annotate stackList with frame boundary
            // no-op for now (we rely on push/pop events)
        } else if (t === "return") {
            // a return: frames unwinding; handled by pop events as they are emitted
        }
        // Render event row too
        // renderEvent(evt);
        const row = document.createElement("div");
        row.textContent = JSON.stringify(evt);
        eventsDiv.appendChild(row)
    }

    function renderStackSnapshot() {
        // We'll show a small inline view inside the memory table as first rows (optional).
        // Simpler: append a small summary row at top of memory table to show top 8 stack entries (addresses & values)
        // Clear any stack snapshot header rows
        // For simplicity, add a top "Stack Top" header before the memory list
        // Implementation: create ephemeral header rows
        // Remove existing stack snapshot rows if present by checking a class
        Array.from(memoryBody.querySelectorAll(".stack-snapshot")).forEach(el => el.remove());
        // Add up to 8 entries
        const snapshot = stackList.slice(0, 8);
        if (snapshot.length === 0) return;
        // create a header row
        const hdr = document.createElement("tr");
        hdr.className = "stack-snapshot";
        hdr.innerHTML = `<td colspan="3" style="background:#222;color:#8ef;border-bottom:1px dashed #444">Stack Top (most recent first)</td>`;
        memoryBody.insertBefore(hdr, memoryBody.firstChild);
        for (let s of snapshot) {
            const row = document.createElement("tr");
            row.className = "stack-snapshot";
            const hex = "0x" + ((s.value >>> 0).toString(16).padStart(8, "0")).toUpperCase();
            row.innerHTML = `<td>${s.addr}</td><td>${hex}</td><td>${s.value >>> 0}</td>`;
            memoryBody.insertBefore(row, memoryBody.firstChild.nextSibling);
        }
    }

    // Step / step over helpers
    function hasMoreEvents() { return eventIndex < simulationEvents.length; }

    function stepOnce() {
        if (!hasMoreEvents()) return;
        const evt = simulationEvents[eventIndex++];
        handleEvent(evt);
    }

    function stepOver() {
        // If next instruction is a CALL (we will inspect upcoming events),
        // advance events until and including the matching 'return' event.
        if (!hasMoreEvents()) return;
        const next = simulationEvents[eventIndex];
        if (next && next.type === "instruction" && next.description && next.description.indexOf("CALL") >= 0) {
            // advance until we see a 'return' event (naive matching)
            let depth = 0;
            while (eventIndex < simulationEvents.length) {
                const e = simulationEvents[eventIndex++];
                handleEvent(e);
                if (e.type === "push_frame") depth++;
                if (e.type === "return") {
                    if (depth <= 0) break;
                    depth--;
                }
                // safety: break if too many
            }
            return;
        }
        // otherwise just one step
        stepOnce();
    }

    // Wire up buttons
    assembleBtn.addEventListener("click", async () => {
        const source = srcArea.value;
        const res = await fetch("/assemble", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source })
        });
        const j = await res.json();
        symbolsDiv.innerText = JSON.stringify(j.symbols || {}, null, 2);
        if (j.errors && j.errors.length){ 
            alert("Assemble errors:\n" + j.errors.join("\n"));
            return;
        }
        // Reset frontend state on a successful assemble to avoid stale events
        resetFrontendState();
        runBtn.disabled = false;
        stepBtn.disabled = false;
        stepOverBtn.disabled = false;
    });

    window.addEventListener("load", function (){
        runBtn.addEventListener("click", async () => {
            const source = srcArea.value;
            const res = await fetch("/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ source })
            });
            const j = await res.json();
            if (j.errors && j.errors.length) {
                alert("Runtime errors:\n" + j.errors.join("\n"));
                return;
            }
            // store events
            simulationEvents = j.events || [];
            console.log("EVENT COUNT:", simulationEvents.length);

            eventsDiv.innerHTML = "";

            for (let e of simulationEvents) {
                const d = document.createElement("div");
                d.textContent = e.type + " → " + e.description;
                eventsDiv.appendChild(d);
            }

            steps = [];

            for (let evt of simulationEvents){
                if (evt.type === "push"){
                    steps.push({
                        type: "push",
                        slots: [{
                            address: evt.data.addr,
                            level: 1,
                            type: evt.data.what || "value",
                            name: String(evt.data.value)
                        }]
                    });
                }

                if (evt.type === "pop"){
                    steps.push({
                        type: "pop",
                        slots: [{
                            address: evt.data.addr,
                            level: 1,
                            type: evt.data.what || "value",
                            name: String(evt.data.value || "")
                        }]
                    });
                }
            }

            stackList.innerHTML = "";
            log.innerHTML = "";

            await animateStackFilling();
            initializeFramePointer();

            // reset UI cleanly
            eventsDiv.innerHTML = "";
            stackList = [];
            memoryMap = {};
            registers = {};
            renderRegisterGrid();
            renderMemoryTable();

            // play events visually
            let i = 0;
            const pace = 150;

            function playNext() {
                if (i >= simulationEvents.length) return;
                handleEvent(simulationEvents[i++]);
                setTimeout(playNext, pace);
            }

            playNext();
        });
    });

    stepBtn.addEventListener("click", () => {
        // If we don't have events loaded, ask the server to return a short run (max_steps=1)
        if (simulationEvents.length === 0) {
            (async () => {
                const res = await fetch("/simulate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ source: srcArea.value })
                });
                const j = await res.json();
                if (j.errors && j.errors.length) {
                    alert("Runtime errors:\n" + j.errors.join("\n"));
                    return;
                }
                simulationEvents = j.events || [];
                eventIndex = 0;
                stepOnce();
            })();
        } else {
            stepOnce();
        }
    });

    stepOverBtn.addEventListener("click", () => {
        if (simulationEvents.length === 0) {
            (async () => {
                const res = await fetch("/simulate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ source: srcArea.value })
                });
                const j = await res.json();
                if (j.errors && j.errors.length) {
                    alert("Runtime errors:\n" + j.errors.join("\n"));
                    return;
                }
                simulationEvents = j.events || [];
                eventIndex = 0;
                stepOver();
            })();
        } else {
            stepOver();
        }
    });

    resetBtn.addEventListener("click", () => {
        resetFrontendState();
        srcArea.value = "";
        symbolsDiv.innerText = "";
    });

    loadSampleBtn.addEventListener("click", () => {
        const sample = `
        ORIGIN 100
        MOVE #2,R1        
        MOVE #3,R2        
        MOVE #0,R0        
        ADD R1,R0         
        ADD R2,R0         
        MOVE R0,X         
        ORIGIN 200
        X: RESERVE 4      
        END
        `;
        srcArea.value = sample;
    });

    // initial render
    renderRegisterGrid();
    renderMemoryTable();
});
