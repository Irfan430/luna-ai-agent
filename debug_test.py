import traceback
import sys

try:
    import live_test
    live_test.run_live_test()
except Exception:
    traceback.print_exc()
    sys.exit(1)
