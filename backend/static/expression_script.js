// Expression Evaluation Script for Postfix and Prefix modes
let currentStack = [];
let currentTimeline = [];
let currentStep = 0;
let speechEnabled = true;

function speak(text) {
    if (speechEnabled && 'speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        speechSynthesis.speak(utterance);
    }
}

function addLog(message) {
    const log = document.getElementById('log');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = message;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    speak(message);
}

function resetStack() {
    currentStack = [];
    currentTimeline = [];
    currentStep = 0;
    document.getElementById('stack').innerHTML = '';
    document.getElementById('log').innerHTML = '';
}

async function evaluateExpression(mode) {
    resetStack();

    const expression = document.getElementById('expression').value.trim();
    if (!expression) {
        addLog('Error: Please enter an expression');
        return;
    }

    addLog(`Evaluating ${mode} expression: ${expression}`);

    const endpoint = mode === 'postfix' ? '/evaluate_postfix' : '/evaluate_prefix';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expression })
        });

        const timeline = await response.json();

        if (timeline.error) {
            addLog(`Error: ${timeline.error}`);
            return;
        }

        currentTimeline = timeline;
        await animateTimeline();

    } catch (error) {
        addLog(`Error: ${error.message}`);
    }
}

async function animateTimeline() {
    for (const step of currentTimeline) {
        await new Promise(resolve => setTimeout(resolve, 800));

        if (step.type === 'push') {
            pushToStack(step.value);
            addLog(step.description);
        } else if (step.type === 'pop') {
            popFromStack();
            addLog(step.description);
        } else if (step.type === 'result') {
            addLog(`✓ ${step.description}`);
            highlightResult();
        }
    }
}

function pushToStack(value) {
    const stackDiv = document.getElementById('stack');
    const block = document.createElement('div');
    block.className = 'stack-block';
    block.textContent = value;
    block.style.animation = 'slideIn 0.5s ease-out';

    stackDiv.insertBefore(block, stackDiv.firstChild);
    currentStack.push(value);
}

function popFromStack() {
    const stackDiv = document.getElementById('stack');
    if (stackDiv.firstChild) {
        const block = stackDiv.firstChild;
        block.style.animation = 'slideOut 0.5s ease-out';
        setTimeout(() => {
            stackDiv.removeChild(block);
        }, 500);
    }
    currentStack.pop();
}

function highlightResult() {
    const stackDiv = document.getElementById('stack');
    if (stackDiv.firstChild) {
        stackDiv.firstChild.style.background = 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)';
        stackDiv.firstChild.style.transform = 'scale(1.1)';
        stackDiv.firstChild.style.boxShadow = '0 10px 40px rgba(67, 233, 123, 0.5)';
    }
}
