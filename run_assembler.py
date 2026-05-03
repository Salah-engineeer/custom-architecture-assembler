import sys
import subprocess

input_file = sys.argv[1] if len(sys.argv) >= 2 else "in.txt"

print("=== Running Pass 1 ===")
result1 = subprocess.run([sys.executable, "pass1.py", input_file])
if result1.returncode != 0:
    print("Pass 1 failed. Check error.txt")
    sys.exit(1)

print("\n=== Running Pass 2 ===")
result2 = subprocess.run([sys.executable, "out_pass2.txt.py"])
if result2.returncode != 0:
    print("Pass 2 failed. Check error.txt")
    sys.exit(1)

print("\nAssembly complete. Output files: symbTable.txt, PoolTable.txt, intermediate.txt, out_pass2.txt, HTME.txt")

print("\n=== Launching Memory Visualizer ===")
subprocess.run([sys.executable, "gui.py"])
