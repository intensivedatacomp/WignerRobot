import shutil
import subprocess
import threading
import torch
import torchvision
import image_processing
import time

import numpy as np
from PIL import Image, ImageTk
import tkinter as tk

PORT = 5001
TITLE = "Robot Feed"
WIDTH = 600
HEIGHT = 400
LISTEN_HOST = "0.0.0.0"
FRAME_SIZE = WIDTH * HEIGHT * 3

if torch.backends.cuda.is_available():
    device = torch.device("cuda")
    print("Using CUDA")
else:
    device = torch.device("cpu")
    print("Using CPU")
to_tensor = torchvision.transforms.ToTensor()
edge_detector = image_processing.EdgeDetector()


def preprocess_display(frame):
    image = to_tensor(frame)[:3].to(device)
    with torch.no_grad():
        edges = edge_detector.detect(image)

    edges_array = edges.squeeze().detach().cpu().numpy()
    edges_array = np.abs(edges_array)
    if edges_array.max() <= 1.0:
        edges_array = edges_array * 255.0
    edges_array = np.clip(edges_array, 0, 255).astype(np.uint8)
    
    return edges_array


def recv_exact(pipe, size):
    buffer = bytearray()
    while len(buffer) < size:
        chunk = pipe.read(size - len(buffer))
        if not chunk:
            raise ConnectionError("Stream closed")
        buffer.extend(chunk)
    return bytes(buffer)


def close_window(root, stop_event, decoder):
    stop_event.set()
    try:
        decoder.terminate()
        decoder.wait(timeout=2)
    except OSError:
        pass
    except subprocess.TimeoutExpired:
        decoder.kill()
        decoder.wait()
    root.destroy()


def decode_command(ffmpeg):
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        "nobuffer",
        "-flags",
        "low_delay",
        "-probesize",
        "32",
        "-analyzeduration",
        "0",
        "-i",
        f"udp://{LISTEN_HOST}:{PORT}?fifo_size=5000000&overrun_nonfatal=1",
        "-an",
        "-vf",
        f"scale={WIDTH}:{HEIGHT}",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "pipe:1",
    ]


def drain_stderr(process):
    """Continuously read ffmpeg's stderr so its pipe buffer never fills and blocks decoding."""
    if process.stderr is None:
        return
    for line in process.stderr:
        text = line.decode("utf-8", "replace").rstrip()
        if text:
            print(f"[ffmpeg] {text}")


def start_decoder():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available in this conda environment")

    process = subprocess.Popen(
        decode_command(ffmpeg),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise RuntimeError("Could not open ffmpeg stdout")
    threading.Thread(target=drain_stderr, args=(process,), daemon=True).start()
    return process


def receiver_loop(latest, stop_event, decoder):
    stdout = decoder.stdout
    try:
        while not stop_event.is_set():
            payload = recv_exact(stdout, FRAME_SIZE)
            frame = np.frombuffer(payload, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3)).copy()
            latest["raw"] = frame
    except (ConnectionError, OSError):
        pass
    finally:
        if not stop_event.is_set():
            latest["error"] = "Decoder stopped (see console for ffmpeg errors)"
        try:
            decoder.terminate()
        except OSError:
            pass

def processing_loop(latest, stop_event):

    while not stop_event.is_set():

        frame = latest["raw"]

        if frame is None:
            time.sleep(0.001)
            continue

        latest["raw"] = None

        processed = preprocess_display(frame)

        latest["frame"] = processed
        latest["count"] += 1


def refresh_gui(root, image_label, latest, stop_event):
    if stop_event.is_set():
        return

    error = latest["error"]
    if error is not None:
        image_label.configure(image="", text=error, fg="#dddddd")
        image_label.image = None
        return

    if latest["count"] != latest["shown"]:
        latest["shown"] = latest["count"]
        # For displaying curent FPS
        now = time.perf_counter()
        elapsed = now - latest["last_fps_time"]

        if elapsed >= 1.0:
            frames = latest["shown"] - latest["last_fps_count"]
            latest["fps"] = frames / elapsed
            latest["last_fps_time"] = now
            latest["last_fps_count"] = latest["shown"]
        root.title(f"{TITLE} - {latest['fps']:.1f} FPS")

        photo = ImageTk.PhotoImage(image=Image.fromarray(latest["frame"]))
        image_label.configure(image=photo)
        image_label.image = photo

    root.after(10, refresh_gui, root, image_label, latest, stop_event)


def main() -> None:
    root = tk.Tk()
    root.title(TITLE)
    root.configure(bg="#111111")

    image_label = tk.Label(root, bg="#111111", text="Waiting for stream...", fg="#dddddd")
    image_label.pack(fill="both", expand=True)

    # latest = {"raw": None, "frame": None, "count": 0, "shown": 0, "error": None}
    latest = {
        "raw": None,
        "frame": None,
        "count": 0,
        "shown": 0,
        "error": None,
        "fps": 0.0,
        "last_fps_time": time.perf_counter(),
        "last_fps_count": 0,
    }
    stop_event = threading.Event()
    decoder = start_decoder()

    root.protocol("WM_DELETE_WINDOW", lambda: close_window(root, stop_event, decoder))

    threading.Thread(target=receiver_loop, args=(latest, stop_event, decoder), daemon=True).start()
    threading.Thread(target=processing_loop,args=(latest,stop_event),daemon=True).start()
    root.after(10, refresh_gui, root, image_label, latest, stop_event)
    root.mainloop()


if __name__ == "__main__":
    main()