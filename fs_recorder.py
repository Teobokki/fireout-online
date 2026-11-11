"""EX SCREEN RECORDER 2026 - records FIREOUT ONLINE's own rendered frames to an H.264 MP4.
Saves finished clips to the player's Downloads folder (%USERPROFILE%/Downloads on Windows).
No microphone. Game / system audio (WASAPI loopback of what you hear) is always captured when
available; there is no on/off toggle. Frame capture is the game view itself and needs no admin.
©2026 EX ROMANIA/EX INC."""
import os, sys, time, threading, subprocess, shutil, collections, tempfile, wave
from panda3d.core import Texture, GraphicsOutput

BRAND = "EX SCREEN RECORDER 2026"
FPS = 30
MAX_QUEUE = 24
SR = 48000


def downloads_dir():
    """Real Downloads folder (FOLDERID_Downloads on Windows), else ~/Downloads."""
    if os.name == "nt":
        try:
            import ctypes, uuid
            from ctypes import wintypes
            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
            u = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}"); g = GUID()
            g.Data1, g.Data2, g.Data3 = u.fields[0], u.fields[1], u.fields[2]
            for i, b in enumerate(u.bytes[8:]): g.Data4[i] = b
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p)) == 0:
                path = p.value; ctypes.windll.ole32.CoTaskMemFree(p)
                if path: return path
        except Exception:
            pass
        return os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), "Downloads")
    return os.path.join(os.path.expanduser("~"), "Downloads")


def ffmpeg_exe(base=None):
    if base:
        for name in ("ffmpeg/ffmpeg.exe", "ffmpeg/ffmpeg", "ffmpeg.exe"):
            p = os.path.join(base, name)
            if os.path.exists(p): return p
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.exists(p): return p
    except Exception:
        pass
    return shutil.which("ffmpeg")


def _write_wav(path, pcm):
    import numpy as np
    x = (np.clip(pcm, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())


class _SysAudio:
    """Always-on WASAPI loopback of the default output (what you hear). Never a microphone."""
    def __init__(self):
        self.ok = False; self.err = None; self.device = ""
        self._run = False; self._th = None
        self._lock = threading.Lock()
        self._cap = False; self._seg = None

    def start_worker(self):
        if self._run: return
        self._run = True
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def stop_worker(self):
        self._run = False

    def _loop(self):
        try:
            import soundcard as sc
            import numpy as np
            spk = sc.default_speaker(); self.device = spk.name
            mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
            with mic.recorder(samplerate=SR, channels=2, blocksize=SR // 50) as r:
                self.ok = True; self.err = None
                while self._run:
                    d = r.record(numframes=SR // 50)
                    if d is None or len(d) == 0:
                        continue
                    d = np.asarray(d, np.float32)
                    if d.ndim == 1: d = np.stack([d, d], 1)
                    now = time.time()
                    with self._lock:
                        s = self._seg
                        if not self._cap or s is None: continue
                        if s["t0"] is None: s["t0"] = now - len(d) / SR
                        exp = int((now - s["t0"]) * SR)
                        gap = exp - (s["n"] + len(d))
                        if gap > SR // 10:
                            s["chunks"].append(np.zeros((gap, 2), np.float32)); s["n"] += gap
                        s["chunks"].append(d[:, :2]); s["n"] += len(d)
        except Exception as e:
            self.ok = False; self.err = str(e) or e.__class__.__name__

    def begin(self):
        with self._lock:
            self._seg = {"t0": None, "n": 0, "chunks": [], "wall0": time.time()}
            self._cap = True

    def end(self):
        import numpy as np
        with self._lock:
            self._cap = False; s = self._seg; self._seg = None
        if s is None: return None
        a = np.concatenate(s["chunks"], 0) if s["chunks"] else np.zeros((0, 2), np.float32)
        return {"pcm": a, "t0": s["t0"] if s["t0"] is not None else s["wall0"]}


class Recorder:
    def __init__(self, app):
        self.app = app
        self.active = False
        self.proc = None; self.thread = None; self.path = None; self.error = None
        self.tex = None; self.start_t = 0.0; self.written = 0; self.size = None; self.fmt = None
        self.q = collections.deque(); self.cv = threading.Condition(); self.closing = False
        # v1.0.5.5: system / game audio always on (no UI toggle, no microphone)
        self.sys_sound = True
        self._audio = _SysAudio()
        self._audio.start_worker()
        self._tmp_video = None; self._tmpdir = None; self._audio_seg = None
        self._build_indicator()

    def _build_indicator(self):
        from direct.gui.DirectGui import DirectFrame, DGG
        import fs_ui as U
        a = self.app
        o = self.ind = DirectFrame(parent=a.a2dTopRight, frameColor=(0.05, 0.02, 0.04, 0.7),
                                   frameSize=(-0.62, -0.03, -0.14, -0.02), state=DGG.DISABLED)
        DirectFrame(parent=o, frameColor=(0.9, 0.08, 0.08, 1), frameSize=(-0.595, -0.565, -0.105, -0.055), state=DGG.DISABLED)
        self.ind_txt = U.text(o, "REC 00:00", (-0.30, -0.095), 0.036, fg=(1, 0.25, 0.25, 1), font=U.FONT_PLAIN)
        U.text(o, BRAND, (-0.30, -0.125), 0.018, fg=(1, 0.55, 0.55, 1), font=U.FONT_PLAIN)
        o.hide()
        a.task_mgr.add(self._tick_ind, "ex-screen-rec-ind", sort=55)

    def _tick_ind(self, task):
        if self.active and self.ind is not None and not self.ind.is_hidden():
            e = int(self.elapsed())
            try: self.ind_txt.setText("REC %02d:%02d" % (e // 60, e % 60))
            except Exception: pass
        return task.cont

    def elapsed(self):
        return time.time() - self.start_t if self.active else 0.0

    def start(self, out_dir=None):
        if self.active:
            return True
        exe = ffmpeg_exe(getattr(self.app, "BASE", None))
        if not exe:
            self.error = "ffmpeg not found"; return False
        out_dir = out_dir or downloads_dir()
        try: os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.error = "Downloads folder: %s" % e; return False
        win = self.app.win
        self.tex = Texture("ex-screen-rec")
        try:
            win.add_render_texture(self.tex, GraphicsOutput.RTM_copy_ram, GraphicsOutput.RTP_color)
        except Exception as e:
            self.error = "could not capture the game window (%s)" % e; self.tex = None; return False
        self.exe = exe
        self.path = os.path.join(out_dir, "FIREOUT ONLINE Recording %s.mp4" % time.strftime("%Y-%m-%d %H-%M-%S"))
        try:
            self._tmpdir = tempfile.mkdtemp(prefix="FSRec_")
            self._tmp_video = os.path.join(self._tmpdir, "video.mp4")
        except Exception as e:
            self.error = "temp: %s" % e; self.tex = None; return False
        self.proc = None; self.size = None; self.fmt = None; self.written = 0; self.error = None
        self.q.clear(); self.closing = False
        self._audio_seg = None
        try: self._audio.begin()
        except Exception: pass
        self.start_t = time.time()
        self.active = True
        try: self.ind.show()
        except Exception: pass
        self.app.task_mgr.add(self._grab, "ex-screen-rec-grab", sort=60)
        return True

    def _open_ffmpeg(self, w, h, pix):
        cmd = [self.exe, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", pix, "-s", "%dx%d" % (w, h), "-r", str(FPS), "-i", "-",
               "-vf", "vflip,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
               "-metadata", "comment=" + BRAND,
               "-metadata", "title=FIREOUT ONLINE Recording", self._tmp_video]
        flags = 0x08000000 if os.name == "nt" else 0
        env = {k: v for k, v in os.environ.items() if not (k.upper().startswith("_PYI") or k.upper().startswith("_MEIPASS"))}
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                     creationflags=flags, env=env)
        self.thread = threading.Thread(target=self._writer, daemon=True)
        self.thread.start()

    def _grab(self, task):
        if not self.active:
            return task.done
        t = self.tex
        if not t.has_ram_image():
            return task.cont
        w, h = t.get_x_size(), t.get_y_size()
        if self.size is None:
            comps = t.get_num_components()
            if t.get_component_width() != 1 or comps not in (3, 4):
                self.error = "unsupported frame format"; self.stop(); return task.done
            self.size, self.fmt = (w, h), ("bgra" if comps == 4 else "bgr24")
            self._open_ffmpeg(w, h, self.fmt)
        if (w, h) != self.size:
            data = None
        else:
            data = bytes(memoryview(t.get_ram_image()))
        due = int((time.time() - self.start_t) * FPS) + 1 - self.written
        if due <= 0:
            return task.cont
        with self.cv:
            if data is not None and len(self.q) < MAX_QUEUE:
                self.q.append([data, due])
            elif self.q:
                self.q[-1][1] += due
            elif data is not None:
                self.q.append([data, due])
            else:
                self.q.append([None, due])
            self.written += due
            self.cv.notify()
        return task.cont

    def _writer(self):
        last = None
        try:
            while True:
                with self.cv:
                    while not self.q and not self.closing:
                        self.cv.wait(0.5)
                    if not self.q and self.closing:
                        break
                    data, n = self.q.popleft()
                if data is None:
                    data = last
                if data is None:
                    continue
                last = data
                for _ in range(n):
                    self.proc.stdin.write(data)
        except Exception as e:
            self.error = "encoder: %s" % e
        finally:
            try: self.proc.stdin.close()
            except Exception: pass

    def stop_async(self, done):
        if not self.active:
            return False
        self.active = False
        try: self.app.task_mgr.remove("ex-screen-rec-grab")
        except Exception: pass
        try: self.ind.hide()
        except Exception: pass
        res = {}
        def work():
            res["path"] = self._finalise()
        self._detach()
        th = threading.Thread(target=work, daemon=True); th.start()
        def poll(task):
            if th.is_alive():
                return task.cont
            done(res.get("path"))
            return task.done
        self.app.task_mgr.add(poll, "ex-screen-rec-finalise")
        return True

    def _detach(self):
        try: self.app.win.clear_render_textures()
        except Exception: pass
        self.tex = None

    def stop(self, timeout=30):
        if not self.active:
            return None
        self.active = False
        try: self.app.task_mgr.remove("ex-screen-rec-grab")
        except Exception: pass
        try: self.ind.hide()
        except Exception: pass
        self._detach()
        return self._finalise(timeout)

    def _mux(self, video, audio_pcm, out):
        """Mux H.264 video + PCM system audio into a YouTube-ready MP4. Falls back to video-only copy."""
        flags = 0x08000000 if os.name == "nt" else 0
        env = {k: v for k, v in os.environ.items() if not (k.upper().startswith("_PYI") or k.upper().startswith("_MEIPASS"))}
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        if audio_pcm is not None and len(audio_pcm.get("pcm", [])) > 0:
            wav = os.path.join(self._tmpdir or os.path.dirname(out), "audio.wav")
            try:
                _write_wav(wav, audio_pcm["pcm"])
                cmd = [self.exe, "-hide_banner", "-loglevel", "error", "-y",
                       "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a",
                       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "2",
                       "-shortest", "-movflags", "+faststart",
                       "-metadata", "comment=" + BRAND,
                       "-metadata", "title=FIREOUT ONLINE Recording", out]
                r = subprocess.run(cmd, capture_output=True, creationflags=flags, env=env, timeout=120)
                if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
                    return True
            except Exception:
                pass
        try:
            shutil.copy2(video, out)
            return os.path.exists(out) and os.path.getsize(out) > 0
        except Exception:
            return False

    def _cleanup_tmp(self):
        td = self._tmpdir; self._tmpdir = None; self._tmp_video = None
        if td:
            try: shutil.rmtree(td, ignore_errors=True)
            except Exception: pass

    def _finalise(self, timeout=30):
        self.active = False
        try: self._audio_seg = self._audio.end()
        except Exception: self._audio_seg = None
        if self.proc is None:
            self._cleanup_tmp(); return None
        with self.cv:
            self.closing = True; self.cv.notify()
        if self.thread: self.thread.join(timeout)
        try: self.proc.wait(timeout)
        except Exception:
            try: self.proc.kill()
            except Exception: pass
            self.error = "encoder timed out"
        ok_v = self.proc.returncode == 0 and self._tmp_video and os.path.exists(self._tmp_video) and os.path.getsize(self._tmp_video) > 0
        if not ok_v and not self.error:
            try: err = (self.proc.stderr.read() or b"").decode("utf-8", "ignore")[-200:]
            except Exception: err = ""
            self.error = err or "encoder failed"
        self.proc = None
        out = None
        if ok_v:
            if self._mux(self._tmp_video, self._audio_seg, self.path):
                out = self.path
            else:
                self.error = self.error or "mux failed"
        self._cleanup_tmp()
        return out
