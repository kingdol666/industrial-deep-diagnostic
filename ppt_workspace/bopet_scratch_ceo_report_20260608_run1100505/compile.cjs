const fs = require('fs');
const path = require('path');
const pptxgen = require('/Users/haozhengzhang/.cc-switch/skills/ppt-auto-builder/node_modules/pptxgenjs');
const html2pptx = require('/Users/haozhengzhang/.cc-switch/skills/huashu-slides/scripts/html2pptx.js');

const ROOT = __dirname;
const SLIDES_DIR = path.join(ROOT, 'slides');
const RUN_DIR = path.resolve(ROOT, '../../workspace/diagnostic-runs/202606081100505_BOPET_scratch_diagnosis/03_figures');

const IMAGE_MAP = {
  'img-model': path.join(RUN_DIR, 'fig1_scratch_by_model.png'),
  'img-scatter': path.join(RUN_DIR, 'fig3_w1c80_std_vs_scratch.png'),
  'img-trends': path.join(RUN_DIR, 'fig4_per_model_scratch_trends.png'),
  'img-temp': path.join(RUN_DIR, 'fig2_temperature_zone_profile.png'),
  'img-overlay': path.join(RUN_DIR, 'fig_master_time_aligned_overlay.png')
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Codex';
  pptx.company = 'OpenAI';
  pptx.subject = 'BOPET scratch diagnosis CEO report';
  pptx.title = 'BOPET划伤诊断老板汇报';
  pptx.lang = 'zh-CN';

  const slideFiles = fs.readdirSync(SLIDES_DIR)
    .filter((file) => /^slide-\d+\.html$/.test(file))
    .sort((a, b) => Number(a.match(/\d+/)[0]) - Number(b.match(/\d+/)[0]));

  for (const slideFile of slideFiles) {
    const htmlPath = path.join(SLIDES_DIR, slideFile);
    const { slide, placeholders } = await html2pptx(htmlPath, pptx);
    for (const ph of placeholders) {
      const imgPath = IMAGE_MAP[ph.id];
      if (imgPath && fs.existsSync(imgPath)) {
        slide.addImage({ path: imgPath, x: ph.x, y: ph.y, w: ph.w, h: ph.h });
      }
    }
  }

  const outPath = path.join(ROOT, 'BOPET_划伤诊断老板汇报_20260608.pptx');
  await pptx.writeFile({ fileName: outPath });
  const stat = fs.statSync(outPath);
  console.log(JSON.stringify({ outPath, pages: slideFiles.length, size: stat.size }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
