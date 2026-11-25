# Blog media (v2)

Plain-language visuals for the blog post "Lost in Selection, Not in Translation". Every card shows unedited
rows of the run files (`runs/`, summarised in `analysis/figures_final/examples.md`); nothing is re-typed by hand.

| File | What it shows |
|---|---|
| `hook_card.html` | Qwen2.5-3B, Marathi: books 2A after being told not to, then searches for a station called «मध्ये» ("in") |
| `pipeline_plain.html` | How one request is tested: model and railway go back and forth, then a program grades the result |
| `gif_frame_0..8.html` + `make_gif.py` | The walkthrough GIF: task T35 in five languages, Gemma-4-26B's tool calls in Hindi, the check, the results |
| `trace_en_vs_mr.html` | The same task in English and Marathi, Qwen2.5-14B |
| `station_skip.html` | Llama-3.1-8B skips `resolve_station` (T07, Hindi) |
| `comic.html` | What we expected to trip up the agent, and what actually did |

The three result charts are drawn by `analysis/blog_v2_figures.py` from `analysis/results_final/`.

Rebuild (needs Node with Playwright, and Pillow):

    cd blog_media && node make_media.js && python3 make_gif.py
    cd .. && python -m analysis.blog_v2_figures

Fonts: Noto Sans and Source Serif 4 (SIL Open Font License, see `fonts/OFL-LICENSE.txt`), via Fontsource.
