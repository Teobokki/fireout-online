"""v1.0.3: re-sculpt ANA's body (arms hanging at the sides) + trousers/belt/buckle (no pocket hand bulge); keeps head & hair."""
import sys, numpy as np
sys.path.insert(0, '/workspace/fireout-shine-concept/src')
import character as C
old = dict(np.load('/workspace/fireout-shine-concept/cache/char.npz'))
_sv = np.savez
def merged(path, **kw):
    old.update(kw); _sv(path, **old)
C.np.savez = merged
C.main(only=['body', 'trousers', 'belt', 'buckle'])
