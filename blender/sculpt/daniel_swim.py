"""DANIEL swim variant: bare legs + feet, swim shorts, flip-flops -> cache_daniel/char_swim.npz"""
import sys, numpy as np
sys.path.insert(0, '/workspace/fireout-shine-concept/src')
import daniel            # applies Daniel's anatomy patches to character module
import ana_outfits_lib as A
C = A.C
out = {}
A.mesh(out, 'legsk', A.legs_skin, (-0.29, -0.25, -0.002), (0.29, 0.16, 1.0), 0.0022)
def shorts(p): return C.trousers_sdf(p) - 0.004
def shorts_keep(c): return (c[:, 2] > 0.62) & (c[:, 2] < 1.0)
A.mesh(out, 'shorts', shorts, (-0.27, -0.19, 0.58), (0.29, 0.19, 1.04), 0.0022, shorts_keep)
for sd in ('R', 'L'):
    a = C.S['ank' + sd]
    A.mesh(out, 'ff' + sd, lambda p, s=sd: A.flipflop(p, s), (a[0] - 0.13, a[1] - 0.25, -0.006), (a[0] + 0.13, a[1] + 0.13, 0.05), 0.0012)
np.savez('/workspace/fireout-shine-concept/cache_daniel/char_swim.npz', **out); print('SWIM OK')
