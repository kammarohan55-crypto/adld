from engine import simulate

code = """
def add(a,b):
    c = a + b
    return c

def main():
    x = add(2,3)

main()
"""

for step in simulate(code):
    print(step)
