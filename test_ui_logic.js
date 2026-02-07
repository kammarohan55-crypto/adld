
// Mock of the Step Over logic to verify correctness
const events = [
    { id: 1, type: 'instruction', data: { mnemonic: 'MOVE' } },
    { id: 2, type: 'instruction', data: { mnemonic: 'CALL' } }, // Call 1
    { id: 3, type: 'push_frame', data: {} },
    { id: 4, type: 'instruction', data: { mnemonic: 'MOVE' } }, // Inside 1
    { id: 5, type: 'instruction', data: { mnemonic: 'CALL' } }, // Nested Call 2
    { id: 6, type: 'push_frame', data: {} },
    { id: 7, type: 'instruction', data: { mnemonic: 'RET' } }, // Inside 2
    { id: 8, type: 'return', data: {} }, // Return 2
    { id: 9, type: 'instruction', data: { mnemonic: 'RET' } }, // Inside 1
    { id: 10, type: 'return', data: {} }, // Return 1
    { id: 11, type: 'instruction', data: { mnemonic: 'HALT' } }
];

let eventIndex = 0;
let rendered = [];

function renderantion(evt) {
    rendered.push(evt.id);
    console.log(`Rendered [${evt.id}] ${evt.type}`);
}

function stepOver() {
    if (eventIndex >= events.length) return;
    const startEvt = events[eventIndex];
    const isCall = (startEvt.type === "instruction" && startEvt.data.mnemonic === "CALL");

    renderantion(startEvt);
    eventIndex++;

    if (isCall) {
        let depth = 0; // The startEvt doesn't increment depth yet, push_frame does
        while (eventIndex < events.length) {
            const evt = events[eventIndex];

            // In the real UI, we render everything as we skip? Yes, "renderEvent" was called in loop.
            renderantion(evt);
            eventIndex++;

            if (evt.type === "push_frame") {
                depth++;
            } else if (evt.type === "return") {
                depth--;
                if (depth <= 0) break;
            }
        }
    }
}

console.log("--- Test 1: Step Normal ---");
stepOver(); // Should render id 1
console.log(`Current Index: ${eventIndex} (Expected 1)`);

console.log("\n--- Test 2: Step Over Call ---");
// Current index 1 is CALL (id 2)
stepOver();
// Should render 2, 3, 4, 5, 6, 7, 8, 9, 10
// StartEvt = 2 (CALL).
// Loop:
//   3 (push_frame) -> depth 1
//   4
//   5
//   6 (push_frame) -> depth 2
//   7
//   8 (return) -> depth 1
//   9
//   10 (return) -> depth 0 -> Break
// So index should be at 10? No, index incremented after render.
// 2 rendered, idx=2.
// Loop:
//   3 rendered, idx=3, depth=1
//   ...
//   10 rendered, idx=10, depth=0 -> break.
//   Wait, 10 is the return for Call 1.
//   So we rendered 2..10.
//   Next event is 11.
console.log(`Current Index: ${eventIndex} (Expected 10 - wait, events length is 11, indices 0..10. ID 11 is index 10)`);
// ID 11 is index 10.
// If we rendered ID 10 (index 9), eventIndex became 10.
// So next stepOver should render ID 11.

console.log("\n--- Test 3: Step Final ---");
stepOver(); // Should render 11
console.log(`Current Index: ${eventIndex}`);
