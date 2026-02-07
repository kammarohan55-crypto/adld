import verify_backend
import sys

# Redirect stdout to a file
with open("verify_out_clean.txt", "w", encoding="utf-8") as f:
    sys.stdout = f
    print("Verifying backend with samples...")
    print("\n")
    verify_backend.run_test("Sum-N (Iterative)", verify_backend.SUM_N_ITERATIVE)
    print("\n")
    verify_backend.run_test("Nested Calls (Stack Test)", verify_backend.NESTED_CALLS)
