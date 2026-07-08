import shutil
import subprocess
import threading
import time

import cv2


def preprocess_capture(frame):
    return frame


class VideoClient:
    def __init__(self, target_host, port, width, height, fps, camera=0, encoders=None):
        self.target_host = target_host
        self.port = port
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = camera
        self.encoders = encoders or ["h264_nvenc", "h264_qsv", "h264_amf", "libx264"]
        self.capture = None
        self.encoder = None
        self.pipe = None
        self.running = False
        self.thread = None

    def capture_command(self, ffmpeg, encoder):
        base = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{self.width}x{self.height}",
            "-r",
            str(self.fps),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            encoder,
            "-g",
            str(self.fps),
            "-bf",
            "0",
        ]
        if encoder == "h264_nvenc":
            base += ["-preset", "p1", "-tune", "ll"]
        elif encoder == "h264_qsv":
            base += ["-preset", "veryfast"]
        elif encoder == "h264_amf":
            base += ["-quality", "speed"]
        else:
            base += ["-preset", "ultrafast", "-tune", "zerolatency"]
        base += [
            "-f",
            "mpegts",
            f"udp://{self.target_host}:{self.port}?pkt_size=1316",
        ]
        return base

    @staticmethod
    def drain_stderr(process):
        """Continuously read ffmpeg's stderr so its pipe buffer never fills and blocks encoding."""
        if process.stderr is None:
            return
        for line in process.stderr:
            text = line.decode("utf-8", "replace").rstrip()
            if text:
                print(f"[ffmpeg] {text}", flush=True)

    def probe_encoder(self, ffmpeg, encoder):
        """Encode a single synthetic frame to verify the encoder actually works.

        Hardware encoders (nvenc/qsv/amf) open lazily and only fail on the first
        frame, so checking that the process is merely alive is not enough.
        """
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=black:s={self.width}x{self.height}:r={self.fps}",
            "-frames:v",
            "1",
            "-c:v",
            encoder,
            "-f",
            "null",
            "-",
        ]
        try:
            result = subprocess.run(command, capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            return False, "probe timed out"
        return result.returncode == 0, result.stderr.decode("utf-8", "replace")

    def start_encoder(self):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is not available in this conda environment")
        last_error = None
        for encoder in self.encoders:
            ok, last_error = self.probe_encoder(ffmpeg, encoder)
            if not ok:
                print(f"Encoder {encoder} unavailable, trying next")
                continue
            try:
                process = subprocess.Popen(
                    self.capture_command(ffmpeg, encoder),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("ffmpeg executable not found") from exc
            print(f"Using encoder: {encoder}", flush=True)
            threading.Thread(target=self.drain_stderr, args=(process,), daemon=True).start()
            return process
        raise RuntimeError(f"Could not start an H.264 encoder: {last_error}")

    def setup_capture(self):
        print(f"Opening camera {self.camera}", flush=True)
        self.capture = cv2.VideoCapture(self.camera)
        if not self.capture.isOpened():
            raise RuntimeError(f"Unable to open camera {self.camera}")
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.capture.set(cv2.CAP_PROP_FPS, self.fps)

    def cleanup(self):
        if self.capture is not None:
            self.capture.release()
        if self.pipe is not None:
            try:
                self.pipe.close()
            except OSError:
                pass
        if self.encoder is not None:
            try:
                self.encoder.terminate()
                self.encoder.wait(timeout=2)
            except OSError:
                pass
            except subprocess.TimeoutExpired:
                self.encoder.kill()
                self.encoder.wait()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        self.setup_capture()
        self.encoder = self.start_encoder()
        self.pipe = self.encoder.stdin
        if self.pipe is None:
            raise RuntimeError("Could not open ffmpeg stdin")

        frame_interval = 1.0 / self.fps
        last_sent = 0.0
        try:
            while self.running:
                ok, frame = self.capture.read()
                if not ok:
                    continue
                frame = preprocess_capture(frame)
                if frame.shape[0] != self.height or frame.shape[1] != self.width:
                    frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)
                try:
                    self.pipe.write(frame.tobytes())
                except BrokenPipeError:
                    print("Encoder exited; stopping capture", flush=True)
                    break
                if frame_interval > 0:
                    now = time.time()
                    sleep_time = frame_interval - (now - last_sent)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    last_sent = time.time()
        except BrokenPipeError as exc:
            print(f"Encoder pipe closed: {exc!r}", flush=True)
        except (ConnectionResetError, OSError) as exc:
            print(f"Video client stopped: {exc!r}", flush=True)
            raise
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join()