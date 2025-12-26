import sys, importlib

importlib.invalidate_caches()
try:
    import numpy as np

    print("numpy file:", getattr(np, "__file__", "built-in"))
except Exception as e:
    print("numpy import error:", e)
print("\nPython sys.path:")
for p in sys.path:
    print(p)
