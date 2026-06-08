const pptxgen = require('pptxgenjs');
const html2pptx = require(process.env.HOME + '/.claude/skills/huashu-slides/scripts/html2pptx.js');
const path = require('path');
const fs = require('fs');

const ROOT = __dirname;
const SLIDES_DIR = path.join(ROOT, 'slides');
const RUN_DIR = path.resolve(ROOT, '../../workspace/diagnostic-runs/202606080227085_BOPET_scratch_analysis/03_figures');

const IMAGE_MAP = {
  'img-variance': path.join(RUN_DIR, 'fig_variance_decomposition.png'),
  'img-products': path.join(RUN_DIR, 'fig_product_timelines.png'),
  'img-corr': path.join(RUN_DIR, 'fig_torque_correlation.png'),
  'img-overlay': path.join(RUN_DIR, 'fig_master_time_aligned_overlay.png'),
  'img-zone': path.join(RUN_DIR, 'fig_zone_profile.png')
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Codex';
  pptx.company = 'OpenAI';
  pptx.subject = 'BOPET scratch CEO report';
  pptx.title = 'BOPET划伤老板汇报';
  pptx.lang = 'zh-CN';

  const slideFiles = fs.readdirSync(SLIDES_DIR)
    .filter((f) => /^slide-\d+\.html$/.test(f))
    .sort((a, b) => Number(a.match(/\d+/)[0]) - Number(b.match(/\d+/)[0]));

  for (const htmlFile of slideFiles) {
    const htmlPath = path.join(SLIDES_DIR, htmlFile);
    const { slide, placeholders } = await html2pptx(htmlPath, pptx);
    for (const ph of placeholders) {
      const imgPath = IMAGE_MAP[ph.id];
      if (imgPath && fs.existsSync(imgPath)) {
        slide.addImage({ path: imgPath, x: ph.x, y: ph.y, w: ph.w, h: ph.h });
      }
    }
  }

  const outPath = path.join(ROOT, 'BOPET_划伤问题老板汇报_20260608.pptx');
  await pptx.writeFile({ fileName: outPath });
  const stat = fs.statSync(outPath);
  console.log(JSON.stringify({ outPath, pages: slideFiles.length, size: stat.size }, null, 2));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
