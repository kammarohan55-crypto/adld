// =============================================
// IMMERSIVE STACK VISUALIZATION - ENHANCED
// =============================================

let fpIndex = null;
let steps = [];
let popIndex = 0;
let isUnwinding = false;

/**
 * Run button - Fetch and animate stack filling level by level
 */
async function run() {
    // Reset state
    stack.innerHTML = "";
    log.innerHTML = "";
    fpIndex = null;
    popIndex = 0;
    isUnwinding = false;

    // Add initial log entry
    addLogEntry("🚀 Starting execution...", "info");

    try {
        // Fetch execution timeline from backend
        let res = await fetch("/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code.value })
        });

        steps = await res.json();

        // Animate stack filling level by level
        await animateStackFilling();

        // Initialize FP at the saved_fp (old frame pointer) position
        initializeFramePointer();

        addLogEntry("✓ Stack constructed successfully!", "success");
    } catch (error) {
        addLogEntry("✗ Error: " + error.message, "error");
    }
}

/**
 * Animate stack filling with level-based cascading
 */
async function animateStackFilling() {
    // Collect all slots from push operations
    let allSlots = [];
    for (let step of steps) {
        if (step.type === "push") {
            allSlots.push(...step.slots);
        }
    }

    // Group slots by level
    let level1Slots = allSlots.filter(s => s.level === 1);
    let level2Slots = allSlots.filter(s => s.level === 2);
    let level3Slots = allSlots.filter(s => s.level === 3);

    // Animate Level 1 (Parameters)
    addLogEntry("📊 Level 1: Loading parameters...", "info");
    for (let slot of level1Slots) {
        await drawSlotAnimated(slot, 200);
    }
    await sleep(300);

    // Animate Level 2 (Return address & Saved FP)
    addLogEntry("📊 Level 2: Setting return address & frame pointer...", "info");
    for (let slot of level2Slots) {
        await drawSlotAnimated(slot, 200);
    }
    await sleep(300);

    // Animate Level 3 (Registers & Local variables)
    addLogEntry("📊 Level 3: Allocating registers & local variables...", "info");
    for (let slot of level3Slots) {
        await drawSlotAnimated(slot, 200);
    }
}

/**
 * Draw a single stack slot with animation
 */
async function drawSlotAnimated(slot, delay) {
    let row = document.createElement("div");
    row.className = "row";
    row.dataset.level = slot.level;
    row.dataset.type = slot.type;

    // Address display (left side, outside stack)
    let addr = document.createElement("div");
    addr.className = "addr";
    addr.innerHTML = `<span class="address-val">0x${slot.address.toString(16).toUpperCase().padStart(4, '0')}</span><br><span class="level-val">L${slot.level}</span>`;

    // Stack slot block
    let block = document.createElement("div");
    block.className = "stackSlot";
    block.dataset.level = slot.level;
    block.innerHTML = `<div class="slot-type">${slot.type.replace(/_/g, ' ')}</div><div class="slot-name">${slot.name}</div>`;

    row.appendChild(addr);
    row.appendChild(block);
    stack.appendChild(row);

    // Trigger animation
    await sleep(50);
    row.classList.add("animate-in");

    await sleep(delay);
}

/**
 * Initialize frame pointer at saved_fp position
 */
function initializeFramePointer() {
    let rows = document.querySelectorAll(".row");

    // Find the saved_fp row (old frame pointer)
    // Convert NodeList to array to use findIndex
    let rowsArray = Array.from(rows);
    for (let i = 0; i < rowsArray.length; i++) {
        if (rowsArray[i].dataset.type === "saved_fp") {
            fpIndex = i;
            updateFPIndicator();

            let addr = rowsArray[i].querySelector(".addr").innerText;
            let slotName = rowsArray[i].querySelector(".slot-name").innerText;
            addLogEntry(`🎯 FP initialized → ${slotName} at ${addr.split('\n')[0]}`, "fp");
            break;
        }
    }
}

/**
 * Move frame pointer up or down
 * @param {number} dir - Direction: -1 for up (+FP), +1 for down (-FP)
 */
function moveFP(dir) {
    let rows = document.querySelectorAll(".row");
    if (rows.length === 0) {
        addLogEntry("⚠ No stack frames available", "warning");
        return;
    }

    // Initialize FP if not set
    if (fpIndex === null) {
        initializeFramePointer();
        return;
    }

    // Move FP
    fpIndex += dir;
    fpIndex = Math.max(0, Math.min(fpIndex, rows.length - 1));

    updateFPIndicator();

    // Log the movement
    let addr = rows[fpIndex].querySelector(".addr .address-val").innerText;
    let slotType = rows[fpIndex].querySelector(".slot-type").innerText;
    let slotName = rows[fpIndex].querySelector(".slot-name").innerText;

    let direction = dir === -1 ? "↑" : "↓";
    addLogEntry(`${direction} FP moved → ${slotType}: ${slotName} at ${addr}`, "fp");
}

/**
 * Update visual FP indicator
 */
function updateFPIndicator() {
    let rows = document.querySelectorAll(".row");

    // Clear all FP indicators
    rows.forEach(r => r.classList.remove("fp-active"));

    // Set current FP indicator
    if (fpIndex !== null && fpIndex >= 0 && fpIndex < rows.length) {
        rows[fpIndex].classList.add("fp-active");
    }
}

/**
 * Unwind stack - Pop elements one by one with animation
 */
async function unwind() {
    if (isUnwinding) {
        addLogEntry("⚠ Already unwinding...", "warning");
        return;
    }

    if (popIndex >= steps.length) {
        addLogEntry("⚠ No more items to unwind", "warning");
        return;
    }

    isUnwinding = true;
    addLogEntry("🔄 Starting stack unwinding...", "info");

    await unwindNext();
}

/**
 * Unwind next element recursively
 */
async function unwindNext() {
    if (popIndex >= steps.length) {
        isUnwinding = false;
        addLogEntry("✓ Stack unwinding complete!", "success");
        return;
    }

    let step = steps[popIndex++];

    if (step.type === "pop") {
        // Since we're using column-reverse, the first child is the topmost (last added) element
        let topRow = stack.firstChild;

        if (topRow) {
            // Animate out
            topRow.classList.add("animate-out");

            // Log the pop operation
            addLogEntry(
                `⬆ Popped ${step.slot.type.replace(/_/g, ' ')}: ${step.slot.name} ` +
                `at 0x${step.slot.address.toString(16).toUpperCase().padStart(4, '0')} [Level ${step.slot.level}]`,
                "pop"
            );

            await sleep(400);
            stack.removeChild(topRow);

            // Update FP if needed
            if (fpIndex !== null) {
                let rows = document.querySelectorAll(".row");
                if (fpIndex >= rows.length) {
                    fpIndex = rows.length - 1;
                    updateFPIndicator();
                }
            }
        }
    }

    // Continue unwinding with delay
    setTimeout(unwindNext, 600);
}

/**
 * Add styled log entry
 */
function addLogEntry(message, type = "info") {
    let entry = document.createElement("div");
    entry.className = "log-entry";

    // Add timestamp
    let timestamp = new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    let color = "#a0a0b0";
    switch (type) {
        case "success":
            color = "#00ffaa";
            break;
        case "error":
            color = "#ff4444";
            break;
        case "warning":
            color = "#ffaa00";
            break;
        case "fp":
            color = "#ff00ff";
            break;
        case "pop":
            color = "#00d4ff";
            break;
    }

    entry.innerHTML = `<span style="color: ${color}; opacity: 0.6;">[${timestamp}]</span> <span style="color: ${color};">${message}</span>`;
    log.appendChild(entry);

    // Auto-scroll to bottom
    log.scrollTop = log.scrollHeight;
}

/**
 * Sleep utility for animations
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
