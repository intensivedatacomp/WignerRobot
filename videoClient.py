import shutil
import subprocess
import threading
import time

import cv2

TARGET_HOST = "127.0.0.1"
PORT = 5001
CAMERA = 0
WIDTH = 600
HEIGHT = 400
FPS = 60
ENCODERS = ["h264_nvenc", "h264_qsv", "h264_amf", "libx264"]

def preprocess_capture(frame):
    return frame


def capture_command(ffmpeg, encoder):
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
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        encoder,
        "-g",
        str(FPS),
        "-bf",
        "0",
        "-flush_packets",
        "1",
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
        f"udp://{TARGET_HOST}:{PORT}?pkt_size=1316",
    ]
    return base


def drain_stderr(process):
    """Continuously read ffmpeg's stderr so its pipe buffer never fills and blocks encoding."""
    if process.stderr is None:
        return
    for line in process.stderr:
        text = line.decode("utf-8", "replace").rstrip()
        if text:
            print(f"[ffmpeg] {text}", flush=True)


def probe_encoder(ffmpeg, encoder):
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
        f"color=black:s={WIDTH}x{HEIGHT}:r={FPS}",
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


def start_encoder():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available in this conda environment")
    last_error = None
    for encoder in ENCODERS:
        ok, last_error = probe_encoder(ffmpeg, encoder)
        if not ok:
            print(f"Encoder {encoder} unavailable, trying next")
            continue
        try:
            process = subprocess.Popen(
                capture_command(ffmpeg, encoder),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("ffmpeg executable not found") from exc
        print(f"Using encoder: {encoder}", flush=True)
        threading.Thread(target=drain_stderr, args=(process,), daemon=True).start()
        return process
    raise RuntimeError(f"Could not start an H.264 encoder: {last_error}")


def main():
    print(f"Opening camera {CAMERA}", flush=True)
    capture = cv2.VideoCapture(CAMERA)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open camera {CAMERA}")
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    capture.set(cv2.CAP_PROP_FPS, FPS)

    encoder = start_encoder()
    pipe = encoder.stdin
    if pipe is None:
        raise RuntimeError("Could not open ffmpeg stdin")

    frame_interval = 1.0 / FPS
    last_sent = 0.0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                continue
            frame = preprocess_capture(frame)
            if frame.shape[0] != HEIGHT or frame.shape[1] != WIDTH:
                frame = cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
            try:
                pipe.write(frame.tobytes())
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
        capture.release()
        try:
            pipe.close()
        except OSError:
            pass
        try:
            encoder.terminate()
            encoder.wait(timeout=2)
        except OSError:
            pass
        except subprocess.TimeoutExpired:
            encoder.kill()
            encoder.wait()


if __name__ == "__main__":
    main()