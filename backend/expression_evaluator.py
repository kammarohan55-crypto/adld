"""
Expression Evaluator for Postfix and Prefix expressions
Generates step-by-step stack operations for visualization
"""

def evaluate_postfix(expression):
    """
    Evaluates a postfix expression and returns timeline of stack operations
    Expression format: "3 4 + 2 *" (space-separated)
    """
    tokens = expression.split()
    stack = []
    timeline = []
    operators = {'+', '-', '*', '/', '^'}
    
    for token in tokens:
        if token in operators:
            # Pop two operands
            if len(stack) < 2:
                return {"error": "Invalid expression: insufficient operands"}
            
            b = stack.pop()
            timeline.append({
                "type": "pop",
                "value": b,
                "description": f"Pop operand: {b}"
            })
            
            a = stack.pop()
            timeline.append({
                "type": "pop",
                "value": a,
                "description": f"Pop operand: {a}"
            })
            
            # Perform operation
            if token == '+':
                result = a + b
            elif token == '-':
                result = a - b
            elif token == '*':
                result = a * b
            elif token == '/':
                result = a // b if b != 0 else 0
            elif token == '^':
                result = a ** b
            
            stack.append(result)
            timeline.append({
                "type": "push",
                "value": result,
                "description": f"Evaluate {a} {token} {b} = {result}, Push result: {result}"
            })
        else:
            # Push operand
            try:
                num = int(token)
                stack.append(num)
                timeline.append({
                    "type": "push",
                    "value": num,
                    "description": f"Push operand: {num}"
                })
            except ValueError:
                return {"error": f"Invalid token: {token}"}
    
    if len(stack) != 1:
        return {"error": "Invalid expression: multiple values remaining"}
    
    timeline.append({
        "type": "result",
        "value": stack[0],
        "description": f"Final Result: {stack[0]}"
    })
    
    return timeline


def evaluate_prefix(expression):
    """
    Evaluates a prefix expression and returns timeline of stack operations
    Expression format: "* + 3 4 2" (space-separated)
    Scanned from right to left
    """
    tokens = expression.split()
    tokens.reverse()  # Scan from right to left
    stack = []
    timeline = []
    operators = {'+', '-', '*', '/', '^'}
    
    for token in tokens:
        if token in operators:
            # Pop two operands
            if len(stack) < 2:
                return {"error": "Invalid expression: insufficient operands"}
            
            a = stack.pop()
            timeline.append({
                "type": "pop",
                "value": a,
                "description": f"Pop operand: {a}"
            })
            
            b = stack.pop()
            timeline.append({
                "type": "pop",
                "value": b,
                "description": f"Pop operand: {b}"
            })
            
            # Perform operation
            if token == '+':
                result = a + b
            elif token == '-':
                result = a - b
            elif token == '*':
                result = a * b
            elif token == '/':
                result = a // b if b != 0 else 0
            elif token == '^':
                result = a ** b
            
            stack.append(result)
            timeline.append({
                "type": "push",
                "value": result,
                "description": f"Evaluate {a} {token} {b} = {result}, Push result: {result}"
            })
        else:
            # Push operand
            try:
                num = int(token)
                stack.append(num)
                timeline.append({
                    "type": "push",
                    "value": num,
                    "description": f"Push operand: {num}"
                })
            except ValueError:
                return {"error": f"Invalid token: {token}"}
    
    if len(stack) != 1:
        return {"error": "Invalid expression: multiple values remaining"}
    
    timeline.append({
        "type": "result",
        "value": stack[0],
        "description": f"Final Result: {stack[0]}"
    })
    
    return timeline
