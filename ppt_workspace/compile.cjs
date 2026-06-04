const pptxgen = require('pptxgenjs');
const html2pptx = require(`${process.env.HOME}/.claude/skills/huashu-slides/scripts/html2pptx.js`);
const path = require('path');
const fs = require('fs');

const SLIDES_DIR = __dirname + '/slides';
const IMG_DIR = __dirname + '/garden-gpt-image-2/image';

const IMAGE_MAP = {
  'img-hero': path.join(IMG_DIR, 'p01_cover.png'),
  'img-stretcher': path.join(IMG_DIR, 'fig7_md_stretcher_layout.png'),
  'img-simpson-explain': path.join(IMG_DIR, 'p05_simpson_explain.png'),
  'img-simpson-torque': path.join(IMG_DIR, 'fig_vlm_simpson_torque.png'),
  'img-speed-scratch': path.join(IMG_DIR, 'fig3_speed_scratch_by_model.png'),
  'img-torque-profile': path.join(IMG_DIR, 'fig6_torque_profile_high_vs_low.png'),
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';

  const slideFiles = fs.readdirSync(SLIDES_DIR)
    .filter(f => f.startsWith('slide-') && f.endsWith('.html'))
    .sort((a, b) => parseInt(a.match(/\d+/)[0]) - parseInt(b.match(/\d+/)[0]));

  console.log(`Processing ${slideFiles.length} slides...`);

  for (const htmlFile of slideFiles) {
    const htmlPath = path.join(SLIDES_DIR, htmlFile);
    try {
      const result = await html2pptx(htmlPath, pptx);
      const slide = result.slide;
      const placeholders = result.placeholders;
      for (const p of placeholders) {
        const imgPath = IMAGE_MAP[p.id];
        if (imgPath && fs.existsSync(imgPath)) {
          slide.addImage({ path: imgPath, x: p.x, y: p.y, w: p.w, h: p.h });
          console.log(`  Added ${p.id} -> ${path.basename(imgPath)}`);
        } else if (p.id) {
          console.log(`  MISSING: ${p.id}`);
        }
      }
    } catch (err) {
      console.error(`  ERROR ${htmlFile}: ${err.message}`);
    }
  }

  const outPath = path.join(__dirname, 'BOPET_诊断汇报.pptx');
  await pptx.writeFile({ fileName: outPath });
  const stat = fs.statSync(outPath);
  console.log(`\n✅ ${outPath}`);
  console.log(`   ${(stat.size/1024).toFixed(0)} KB, ${slideFiles.length} pages`);
})();
