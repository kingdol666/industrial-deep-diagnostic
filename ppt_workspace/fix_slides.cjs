/**
 * Transform all slide-*.html files for html2pptx.js compatibility:
 * 1. Change body from flexbox centering to explicit 960pt x 540pt slide
 * 2. Flatten: remove .slide wrapper div, move content to body
 */
const fs = require('fs');
const path = require('path');

const SLIDES_DIR = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/ppt_workspace/slides';

const files = fs.readdirSync(SLIDES_DIR).filter(f => f.match(/^slide-\d+\.html$/)).sort();

files.forEach(file => {
  const filePath = path.join(SLIDES_DIR, file);
  let html = fs.readFileSync(filePath, 'utf8');

  // 1. Fix body CSS: replace flexbox centering with explicit slide dimensions
  html = html.replace(
    /body\s*\{\s*background:\s*#E0E0E0;\s*display:\s*flex;\s*justify-content:\s*center;\s*align-items:\s*center;\s*min-height:\s*100vh;\s*font-family:\s*("Microsoft YaHei",\s*"思源黑体",\s*"Noto Sans SC",\s*sans-serif);\s*\}/,
    'body { width: 960pt; height: 540pt; margin: 0; padding: 0; background: #FAFAFA; overflow: hidden; font-family: $1 }'
  );

  // 2. Remove .slide CSS rule
  html = html.replace(
    /\.slide\s*\{\s*width:\s*960pt;\s*height:\s*540pt;\s*background:\s*#FAFAFA;\s*position:\s*relative;\s*overflow:\s*hidden;\s*box-shadow:[^}]*\}\s*/,
    ''
  );

  // 3. Remove opening <div class="slide">
  html = html.replace(/\s*<div class="slide">\s*/g, '\n');

  // 4. Remove closing </div> right before </body> (the slide wrapper's close)
  html = html.replace(/\s*<\/div>\s*<\/body>/g, '\n</body>');

  // 5. Fix remaining .slide references if any (shouldn't be any but just in case)
  // No - all content uses absolute positioning which works fine on body

  fs.writeFileSync(filePath, html, 'utf8');
  console.log(`Fixed: ${file}`);
});

console.log(`\nAll ${files.length} slides fixed for html2pptx compatibility.`);
