const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');
const html2pptx = require('/Users/haozhengzhang/.claude/skills/huashu-slides/scripts/html2pptx.js');

const SLIDES_DIR = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/ppt_workspace/slides';
const IMAGE_DIR = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/workspace/diagnostic-runs/202605270557262_bopet_md_diagnosis/03_figures';
const OUTPUT = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/ppt_workspace/BOPET_MD_Diagnosis_Report.pptx';

const IMAGE_MAP = {
  'img-defect-ts': '01_defect_timeseries.png',
  'img-simpson': '03_simpson_paradox.png',
  'img-defect-corr': '04_defect_correlations.png',
  'img-md-temp': '06_md_temp_profile.png'
};

async function main() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';

  const files = fs.readdirSync(SLIDES_DIR).filter(f => f.match(/^slide-\d+\.html$/)).sort();

  for (const file of files) {
    const htmlPath = path.join(SLIDES_DIR, file);
    console.log(`Processing ${file}...`);

    const { slide, placeholders } = await html2pptx(htmlPath, pres);

    for (const ph of placeholders) {
      const imgFile = IMAGE_MAP[ph.id];
      if (imgFile) {
        const imgPath = path.join(IMAGE_DIR, imgFile);
        if (fs.existsSync(imgPath)) {
          slide.addImage({ path: imgPath, x: ph.x, y: ph.y, w: ph.w, h: ph.h });
          console.log(`  Inserted ${imgFile} at (${ph.x}, ${ph.y}) ${ph.w}x${ph.h}`);
        } else {
          console.warn(`  WARNING: Image not found: ${imgPath}`);
        }
      }
    }
  }

  await pres.writeFile({ fileName: OUTPUT });
  const stats = fs.statSync(OUTPUT);
  console.log(`\nSUCCESS: ${pres.slides.length} slides, ${(stats.size / 1024).toFixed(1)} KB`);
  console.log(`Output: ${OUTPUT}`);
}

main().catch(err => {
  console.error('COMPILATION FAILED:', err);
  process.exit(1);
});
