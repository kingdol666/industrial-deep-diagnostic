const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/haozhengzhang/.claude/skills/huashu-slides/scripts/html2pptx.js');
const path = require('path');
const fs = require('fs');

const SLIDES_DIR = '/Volumes/laxer/codes/skills/industrial-deep-diagnostic/ppt_workspace/slides';
const IMAGE_DIR = '/Volumes/laxer/codes/skills/industrial-deep-diagnostic/ppt_workspace/garden-gpt-image-2/image';

const IMAGE_MAP = {
  'img-hero': path.join(IMAGE_DIR, 'p01_cover.png'),
  'img-pipeline': path.join(IMAGE_DIR, 'p04_pipeline.png'),
  'img-repair-loop': path.join(IMAGE_DIR, 'p06_repair_loop.png'),
  'img-rag': path.join(IMAGE_DIR, 'p07_rag_arch.png'),
  'img-integrated': path.join(IMAGE_DIR, 'p10_integrated.png'),
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE'; // 16:9 = 13.333" x 7.5"

  // Get sorted slide files
  const files = fs.readdirSync(SLIDES_DIR)
    .filter(f => /^slide-\d+\.html$/.test(f))
    .sort((a, b) => {
      const na = parseInt(a.match(/\d+/)[0]);
      const nb = parseInt(b.match(/\d+/)[0]);
      return na - nb;
    });

  console.log(`Found ${files.length} slides`);

  for (const file of files) {
    const htmlPath = path.join(SLIDES_DIR, file);
    console.log(`Processing ${file}...`);

    try {
      const { slide, placeholders } = await html2pptx(htmlPath, pptx);
      console.log(`  ${placeholders.length} placeholders found`);

      for (const p of placeholders) {
        const imgPath = IMAGE_MAP[p.id];
        if (imgPath && fs.existsSync(imgPath)) {
          slide.addImage({ path: imgPath, x: p.x, y: p.y, w: p.w, h: p.h });
          console.log(`  Added image for ${p.id}`);
        } else {
          console.log(`  WARNING: No image for placeholder "${p.id}"`);
        }
      }
    } catch (err) {
      console.error(`  Error processing ${file}: ${err.message}`);
    }
  }

  const outputPath = '/Volumes/laxer/codes/skills/industrial-deep-diagnostic/ppt_workspace/OUTPUT.pptx';
  await pptx.writeFile({ fileName: outputPath });
  const stat = fs.statSync(outputPath);
  console.log(`PPTX saved to ${outputPath} (${(stat.size / 1024).toFixed(0)} KB)`);
})().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
