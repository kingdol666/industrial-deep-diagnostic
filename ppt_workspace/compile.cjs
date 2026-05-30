const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');
const html2pptx = require('/Users/haozhengzhang/.claude/skills/huashu-slides/scripts/html2pptx.js');

const SLIDES_DIR = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/ppt_workspace/slides';
const IMAGE_DIR = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/workspace/diagnostic-runs/202605280810048_lekai_diagnostic/03_figures';
const OUTPUT = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/ppt_workspace/BOPET_MD_Diagnosis_Report.pptx';

const SLIDE_IMAGE_MAP = {
  'slide-03.html': { 'img-scatter': 'fig_08_key_scatter_by_product.png' },
  'slide-05.html': { 'img-robustness': 'fig_11_spearman_vs_pearson.png' },
  'slide-06.html': { 'img-timeseries': 'fig_03_defect_timeseries_by_product.png' },
  'slide-07.html': { 'img-simpson': 'fig_09_simpson_paradox.png' },
  'slide-08.html': { 'img-cooccurrence': 'fig_06_defect_cooccurrence.png' },
};

async function main() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';

  const files = fs.readdirSync(SLIDES_DIR)
    .filter(f => f.match(/^slide-\d+\.html$/))
    .sort((a, b) => {
      const na = parseInt(a.match(/\d+/)[0]);
      const nb = parseInt(b.match(/\d+/)[0]);
      return na - nb;
    });

  console.log(`Found ${files.length} slides: ${files.join(', ')}`);

  for (const file of files) {
    const htmlPath = path.join(SLIDES_DIR, file);
    console.log(`\nProcessing ${file}...`);

    try {
      const { slide, placeholders } = await html2pptx(htmlPath, pres);

      const slideMap = SLIDE_IMAGE_MAP[file] || {};

      for (const ph of placeholders) {
        const imgFile = slideMap[ph.id];
        if (imgFile) {
          const imgPath = path.join(IMAGE_DIR, imgFile);
          if (fs.existsSync(imgPath)) {
            slide.addImage({ path: imgPath, x: ph.x, y: ph.y, w: ph.w, h: ph.h });
            console.log(`  ✓ Inserted ${imgFile} at (${ph.x.toFixed(2)}, ${ph.y.toFixed(2)}) ${ph.w.toFixed(2)}×${ph.h.toFixed(2)}`);
          } else {
            console.warn(`  ✗ Image not found: ${imgPath}`);
          }
        } else {
          console.warn(`  ✗ No mapping for placeholder "${ph.id}" in ${file}`);
        }
      }

      if (Object.keys(slideMap).length === 0) {
        console.log('  (text-only slide, no images)');
      }
    } catch (err) {
      console.error(`  ✗ Error processing ${file}: ${err.message}`);
    }
  }

  await pres.writeFile({ fileName: OUTPUT });
  const stats = fs.statSync(OUTPUT);
  console.log(`\n✅ SUCCESS: ${pres.slides.length} slides, ${(stats.size / 1024).toFixed(1)} KB`);
  console.log(`Output: ${OUTPUT}`);
}

main().catch(err => {
  console.error('COMPILATION FAILED:', err);
  process.exit(1);
});
