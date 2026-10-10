"""Set the opt-in guest test controller, without sending OS input events."""
import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUTTONS = {"up": 1, "down": 2, "left": 4, "right": 8, "start": 16, "back": 32,
           "ls": 64, "rs": 128, "lb": 256, "rb": 512,
           "a": 4096, "b": 8192, "x": 16384, "y": 32768}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--buttons", default="")
for axis in ("lx", "ly", "rx", "ry", "lt", "rt"):
    parser.add_argument("--" + axis, type=int, default=0)
parser.add_argument("--auto", action="store_true", help="Resume the timed input script")
parser.add_argument("--hold", type=float, default=0, help="Release after this many seconds, at most 10")
parser.add_argument("--latest-frame", help="Integration test label whose most recent render target to convert to PNG")
args = parser.parse_args()
if not 0 <= args.hold <= 10:
    parser.error("Hold duration must be in 0..10 seconds")
if any(not -32768 <= getattr(args, axis) <= 32767 for axis in ("lx", "ly", "rx", "ry")) or any(not 0 <= getattr(args, axis) <= 255 for axis in ("lt", "rt")):
    parser.error("Controller value out of range")
try:
    buttons = sum(BUTTONS[name] for name in set(args.buttons.lower().split(",")) if name)
except KeyError as error:
    parser.error("Unknown button: " + str(error))
path = ROOT / "out/runtime-windows/live-controller.txt"
path.parent.mkdir(parents=True, exist_ok=True)
def write(value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(value + "\n")
    temporary.replace(path)
value = "auto" if args.auto else " ".join(str(v) for v in (buttons, args.lx, args.ly, args.rx, args.ry, args.lt, args.rt))
write(value)
print(json.dumps({"guest_controller": value, "hold_seconds": args.hold}))
if args.latest_frame:
    if not args.latest_frame.replace("-", "").replace("_", "").isalnum():
        parser.error("Invalid test label")
    from PIL import Image
    folder = ROOT / "out/runtime-windows" / args.latest_frame
    frames = sorted(folder.glob("frame-*.ppm"), key=lambda item: int(item.stem.split("-")[1]))
    if frames:
        frame = frames[-1]
        Image.open(frame).save(frame.with_suffix(".png"))
        print(str(frame.with_suffix(".png")))
if args.hold:
    time.sleep(args.hold)
    write("auto" if args.auto else "0 0 0 0 0 0 0")
