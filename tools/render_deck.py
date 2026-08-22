"""Render the deck to PNG using the installed PowerPoint (the true target renderer)."""
import glob
import os
import shutil

import win32com.client

OUT = os.path.abspath("evidence/_deck_png")
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)

app = win32com.client.Dispatch("PowerPoint.Application")
deck = app.Presentations.Open(os.path.abspath("evidence/Milestone_3_Final_Presentation.pptx"),
                              WithWindow=False)
deck.SaveAs(OUT, 18)          # 18 = ppSaveAsPNG
deck.Close()
app.Quit()

files = sorted(glob.glob(os.path.join(OUT, "**", "*.PNG"), recursive=True) +
               glob.glob(os.path.join(OUT, "**", "*.png"), recursive=True))
print("rendered %d slides" % len(files))
for f in files:
    print("  ", f)
