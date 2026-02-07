from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from . import engine
from . import expression_evaluator
from . import assembler, engine_alp

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

@app.route("/")
def home():
    return render_template("menu.html")

@app.route("/function")
def function_mode():
    return render_template("function.html")

@app.route("/nested")
def nested_mode():
    return render_template("nested.html")

@app.route("/postfix")
def postfix_mode():
    return render_template("postfix.html")

@app.route("/prefix")
def prefix_mode():
    return render_template("prefix.html")

@app.route("/alp")
def alp_mode():
    return render_template("alp.html")

@app.route("/assemble", methods=["POST"])
def api_assemble():
    data = request.get_json() or {}
    source = data.get("source", "")
    assembled = assembler.assemble(source)
    # do not send full memory bytes in JSON directly; send memory length and symbols/instructions
    out = {
        "errors": assembled.get("errors", []),
        "symbols": assembled.get("symbols", {}),
        "instructions": [ {"addr":inst["addr"], "mnemonic":inst["mnemonic"], "source":inst["source"]} for inst in assembled.get("instructions",[]) ],
        "memory_size": len(assembled.get("memory", bytearray()))
    }
    return jsonify(out)

@app.route("/simulate", methods=["POST"])
def api_simulate():
    data = request.get_json() or {}
    source = data.get("source", "")
    run_opts = data.get("run_opts", {})
    assembled = assembler.assemble(source)
    if assembled.get("errors"):
        return jsonify({"errors": assembled.get("errors"), "events": []})
    result = engine_alp.simulate(assembled, run_opts=run_opts)
    # To keep response size reasonable, convert memory to base64 or report memory length only.
    # Here we will not include raw memory bytes in the events response; front-end can request memory slices later if needed.
    return jsonify({
        "errors": result.get("errors", []),
        "events": result.get("events", []),
        "final_state_meta": {
            "registers": result.get("final_state", {}).get("registers", {}),
            "memory_size": len(result.get("final_state", {}).get("memory", bytearray()))
        }
    })

@app.route("/step", methods=["POST"])
def api_step():
    """
    Optional convenience: accept already-assembled object (JSON with instructions and memory)
    and a serialized state (registers, memory slice) and execute one instruction returning
    the emitted events and the updated partial state.
    For now, implement a simple step: assemble code + run with max_steps=1 and return events.
    """
    data = request.get_json() or {}
    source = data.get("source", "")
    assembled = assembler.assemble(source)
    if assembled.get("errors"):
        return jsonify({"errors": assembled.get("errors"), "events": []})
    result = engine_alp.simulate(assembled, run_opts={"max_steps":1, "step_limit":1000})
    return jsonify({"errors": result.get("errors", []), "events": result.get("events", []), "final_state_meta": {"memory_size": len(result.get("final_state",{}).get("memory",bytearray()))}})

@app.route("/run", methods=["POST"])
def run():
    code = request.json["code"]
    return jsonify(engine.simulate(code))

@app.route("/evaluate_postfix", methods=["POST"])
def eval_postfix():
    expression = request.json["expression"]
    return jsonify(expression_evaluator.evaluate_postfix(expression))

@app.route("/evaluate_prefix", methods=["POST"])
def eval_prefix():
    expression = request.json["expression"]
    return jsonify(expression_evaluator.evaluate_prefix(expression))

if __name__ == "__main__":
    app.run(debug=True)
