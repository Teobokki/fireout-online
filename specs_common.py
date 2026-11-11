# shared PyInstaller config for FIREOUT ONLINE 1.0.0
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files, collect_all
import os, glob
fd, fb, fh = collect_all('imageio_ffmpeg')
sd, sb, sh = collect_all('soundcard')
try:
    cd, cb, ch = collect_all('cffi')
except Exception:
    cd, cb, ch = [], [], []
try:
    td, tb, th = collect_all('comtypes')
except Exception:
    td, tb, th = [], [], []
DROP = ('avcodec', 'avformat', 'avutil', 'swresample', 'swscale', 'libp3ffmpeg', 'fmod', 'assimp', 'ptloader',
        'bullet', 'pandaode', 'pandaai', 'vrpn', 'p3vision', 'pandadx9', 'd3dx9', 'cgd3d9', 'pandaphysics', 'pandafx')
BINS = [x for x in collect_dynamic_libs('panda3d') if not any(k in os.path.basename(x[0]).lower() for k in DROP)]
DATAS = collect_data_files('panda3d', includes=['etc/*']) + fd + sd + cd + td
BINS = BINS + fb + sb + cb + tb
ASSETS = [(f, 'assets') for f in ('assets/cover.jpg', 'assets/backdrop.jpg', 'assets/icon.ico', 'assets/icon.png', 'assets/ui_font.ttf',
                                  'assets/ui_plain.ttf', 'assets/jp_font.otf', 'assets/THIRD_PARTY.txt')]
ASSETS += [('assets/sfx', 'assets/sfx'), ('assets/voice', 'assets/voice'), ('assets/tex', 'assets/tex')]
ASSETS += [(f, 'assets/models') for f in glob.glob('assets/models/*.bam')]
ASSETS += [(f, 'assets/models') for f in glob.glob('assets/models/*.json')]   # v1.0.3: SELMOTES face patches
HIDDEN = ['panda3d.core', 'panda3d.direct', 'direct.showbase.ShowBase', 'direct.gui.DirectGui', 'direct.filter.CommonFilters', 'direct.filter.FilterManager', 'fs_gfx', 'fs_events',
          'fs_game', 'fs_game_banter', 'fs_world', 'fs_geom', 'fs_vehicle', 'fs_people', 'fs_ai', 'fs_ui', 'fs_data', 'fs_lines',
          'fs_shaders', 'fs_menu_stage', 'fs_weapons', 'fs_miyo', 'fs_vinebuild', 'fs_blocks', 'fs_food', 'fs_laptop', 'fs_browser', 'fs_misto', 'fs_signals', 'fs_citybuild', 'fs_net', 'fs_avatar', 'fs_online', 'fs_sfc', 'fs_recorder', 'fs_hack', 'numpy', 'imageio_ffmpeg', 'soundcard', 'soundcard.mediafoundation', 'cffi', '_cffi_backend', 'comtypes', 'comtypes.client', 'comtypes.stream'] + fh + sh + ch + th
EXCL = ['matplotlib', 'scipy', 'pandas', 'IPython', 'pytest', 'tkinter', 'PIL', 'cv2', 'wx', 'PyQt5', ]   # v1.0.5.5: imageio_ffmpeg + soundcard (WASAPI loopback) for EX SCREEN RECORDER 2026; numpy kept
