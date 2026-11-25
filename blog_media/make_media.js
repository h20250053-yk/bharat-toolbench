// Renders the blog's HTML visuals to PNG (2x) and the walkthrough frames to PNG (1x) for the GIF.
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const shots = [['trace_en_vs_mr', 2], ['station_skip', 2], ['pipeline_plain', 2], ['hook_card', 2], ['comic', 2]];
  for (const [name, dpr] of shots) {
    const p = await b.newPage({ viewport: { width: 600, height: 600 }, deviceScaleFactor: dpr });
    await p.goto('file://' + process.cwd() + '/' + name + '.html'); await p.evaluate(() => document.fonts.ready);
    await p.locator('.wrap').screenshot({ path: name + '.png' }); await p.close();
  }
  for (let k = 0; k <= 8; k++) {
    const p = await b.newPage({ viewport: { width: 600, height: 430 }, deviceScaleFactor: 1 });
    await p.goto('file://' + process.cwd() + '/gif_frame_' + k + '.html'); await p.evaluate(() => document.fonts.ready);
    await p.locator('.wrap').screenshot({ path: 'gif_frame_' + k + '.png' }); await p.close();
  }
  await b.close();
})();
