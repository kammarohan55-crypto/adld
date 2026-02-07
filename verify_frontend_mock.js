
// Mock DOM elements
const document = {
    createElement: (tag) => ({ tag, className: "", innerHTML: "", style: {}, appendChild: () => { } }),
    getElementById: (id) => ({
        id,
        innerHTML: "",
        value: "",
        appendChild: () => { },
        addEventListener: () => { },
        scrollTop: 0,
        scrollHeight: 100,
        querySelectorAll: () => [],
        insertBefore: () => { }
    })
};
global.document = document;

// Mock window and alert
global.window = {};
global.alert = console.log;

// Copy-paste key parts of the new logic to test it in Node
// (Since we can't easily import the browser JS file directly without module exports)
// We will mock the state and event handler to verify logic.

let registers = {};
let memoryMap = {};
let stackList = [];

function renderRegisterGrid() {
    // console.log("Render Registers:", JSON.stringify(registers));
}

function renderMemoryTable() {
    // console.log("Render Memory:", Object.keys(memoryMap).length + " entries");
}

function renderStackSnapshot() {
    // console.log("Render Stack:", stackList.map(s => `[${s.addr}]=${s.value}`));
}

function handleEvent(evt) {
    const t = evt.type;
    if (t === "reg_update") {
        const d = evt.data || {};
        registers[d.reg] = d.new;
    } else if (t === "mem_write") {
        const d = evt.data || {};
        if (typeof d.addr === "number") memoryMap[d.addr] = d.value >>> 0;
    } else if (t === "push") {
        const d = evt.data || {};
        stackList.unshift({ addr: d.addr, value: (d.value >>> 0), what: d.what || "word" });
        memoryMap[d.addr] = (d.value >>> 0);
    } else if (t === "pop") {
        const d = evt.data || {};
        const idx = stackList.findIndex(s => s.addr === d.addr);
        if (idx !== -1) stackList.splice(idx, 1);
    }
}

// Test Suite
console.log("--- Testing Frontend Logic ---");

// 1. Test Register Update
handleEvent({ type: "reg_update", data: { reg: "R0", new: 42 } });
if (registers["R0"] === 42) console.log("PASS: Register Update");
else console.log("FAIL: Register Update", registers);

// 2. Test Memory Write
handleEvent({ type: "mem_write", data: { addr: 200, value: 0xFF } });
if (memoryMap[200] === 255) console.log("PASS: Memory Write");
else console.log("FAIL: Memory Write", memoryMap);

// 3. Test Push
handleEvent({ type: "push", data: { addr: 196, value: 10, what: "word" } });
if (stackList.length === 1 && stackList[0].addr === 196 && memoryMap[196] === 10) console.log("PASS: Push logic");
else console.log("FAIL: Push logic", stackList);

// 4. Test Pop
handleEvent({ type: "pop", data: { addr: 196, value: 10 } });
if (stackList.length === 0) console.log("PASS: Pop logic");
else console.log("FAIL: Pop logic", stackList);

console.log("--- Frontend Logic Verification Complete ---");
