import sys, pathlib, glob, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.video.io import probe
I = r"C:\Users\RAHILA~1\AppData\Local\Temp\claude\inbox2"
for f in sorted(glob.glob(os.path.join(I, "*.mp4"))):
    i = probe(f)
    print("%-24s %dx%d aspect %.4f  %5.2fs  %3d frames  %.1f fps  %.2f MB  9:16=%s" % (
        os.path.basename(f), i["width"], i["height"], i["aspect"], i["duration_s"],
        i["frame_count"], i["fps"], i["file_mb"], i["is_9_16"]))
