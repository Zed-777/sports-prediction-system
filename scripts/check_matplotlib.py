import traceback
import sys
try:
    import matplotlib
    print('matplotlib version:', matplotlib.__version__)
    print('matplotlib __file__:', getattr(matplotlib, '__file__', 'built-in or missing file attr'))
    import matplotlib._c_internal_utils as cutils
    print('matplotlib._c_internal_utils OK, path:', cutils.__file__)
except Exception as e:
    print('matplotlib import error:', type(e).__name__, e)
    traceback.print_exc()
    print('\nsys.path:')
    for p in sys.path:
        print(p)
