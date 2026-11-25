"""Assemble the walkthrough GIF from the rendered frames (4.5 s per frame, 6 s on the start and the two result frames)."""
from PIL import Image
frames = [Image.open(f"gif_frame_{k}.png").convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT) for k in range(0, 9)]
durations = [6000] + [4500] * 6 + [6000, 6000]
frames[0].save("walkthrough_slow.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
