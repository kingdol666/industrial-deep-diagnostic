const fs = require('fs');
const path = require('path');
const pptxgen = require('/Users/haozhengzhang/.cc-switch/skills/ppt-auto-builder/node_modules/pptxgenjs');
const html2pptx = require('/Users/haozhengzhang/.cc-switch/skills/huashu-slides/scripts/html2pptx.js');

const ROOT = __dirname;
const SLIDES_DIR = path.join(ROOT, 'slides');
const FIG_DIR = path.resolve(ROOT, '../../workspace/diagnostic-runs/202606090427156_BOPET薄膜双拉加工/03_figures');

const IMAGE_MAP = {
  'img-model': path.join(FIG_DIR, 'fig_scratch_by_model.png'),
  'img-switch': path.join(FIG_DIR, 'fig_vlm_event_response.png'),
  'img-robust': path.join(FIG_DIR, 'fig_correlation_robustness.png'),
  'img-cluster': path.join(FIG_DIR, 'fig_filter_quench_scatter.png'),
  'img-zone': path.join(FIG_DIR, 'fig_zone_spatial_profile.png')
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Codex';
  pptx.company = 'OpenAI';
  pptx.subject = 'BOPET model-difference diagnosis CEO report';
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

  const outPath = path.join(ROOT, 'BOPET_双拉加工划伤诊断老板汇报_20260609.pptx');
  await pptx.writeFile({ fileName: outPath });
  const stat = fs.statSync(outPath);
  console.log(JSON.stringify({ outPath, pages: slideFiles.length, size: stat.size }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
