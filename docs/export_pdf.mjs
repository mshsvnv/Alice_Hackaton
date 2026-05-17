import puppeteer from 'puppeteer';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const htmlPath = resolve(__dirname, 'pitch_presentation.html');
const outputPath = resolve(__dirname, 'pitch_presentation.pdf');

// Simulate 150% zoom: viewport is 2/3 of 1920x1080
const VIEWPORT_W = 1280;
const VIEWPORT_H = 720;
const DEVICE_SCALE = 2;

async function main() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({
    width: VIEWPORT_W,
    height: VIEWPORT_H,
    deviceScaleFactor: DEVICE_SCALE
  });

  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });

  // Wait for fonts to load
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 1000));

  // Get total slides
  const total = await page.evaluate(() => {
    // eslint-disable-next-line no-undef
    return typeof TOTAL !== 'undefined' ? TOTAL : document.querySelectorAll('.slide').length;
  });

  console.log(`Found ${total} slides. Exporting at 150% zoom (${VIEWPORT_W}x${VIEWPORT_H})...`);

  async function captureSlides(label, hideNav) {
    if (hideNav) {
      await page.evaluate(() => {
        const nav = document.querySelector('.bottomnav');
        const prog = document.querySelector('.progress');
        if (nav) nav.style.display = 'none';
        if (prog) prog.style.display = 'none';
      });
    }

    const screenshots = [];
    for (let i = 1; i <= total; i++) {
      await page.evaluate((n) => {
        // eslint-disable-next-line no-undef
        showSlide(n);
      }, i);
      await new Promise(r => setTimeout(r, 600));
      const screenshot = await page.screenshot({
        type: 'png',
        clip: { x: 0, y: 0, width: VIEWPORT_W, height: VIEWPORT_H }
      });
      screenshots.push(screenshot);
      console.log(`  [${label}] Slide ${i}/${total} captured`);
    }

    if (hideNav) {
      await page.evaluate(() => {
        const nav = document.querySelector('.bottomnav');
        const prog = document.querySelector('.progress');
        if (nav) nav.style.display = '';
        if (prog) prog.style.display = '';
      });
    }

    return screenshots;
  }

  async function savePdf(screenshots, outPath) {
    const imgTags = screenshots.map((buf) => {
      const b64 = buf.toString('base64');
      return `<div style="page-break-after: always; width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center;">
        <img src="data:image/png;base64,${b64}" style="width: 100%; height: 100%; object-fit: contain;">
      </div>`;
    }).join('\n');

    const pdfHtml = `<!DOCTYPE html>
<html>
<head><style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { margin: 0; }
  @page { size: ${VIEWPORT_W}px ${VIEWPORT_H}px; margin: 0; }
</style></head>
<body>${imgTags}</body>
</html>`;

    const pdfPage = await browser.newPage();
    await pdfPage.setContent(pdfHtml, { waitUntil: 'networkidle0' });
    await pdfPage.pdf({
      path: outPath,
      width: `${VIEWPORT_W}px`,
      height: `${VIEWPORT_H}px`,
      printBackground: true,
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
      preferCSSPageSize: true
    });
    await pdfPage.close();
  }

  // Version 1: Clean (no nav)
  console.log('\n--- Clean version (no nav) ---');
  const cleanScreens = await captureSlides('clean', true);
  await savePdf(cleanScreens, outputPath);
  console.log(`PDF saved to: ${outputPath}`);

  // Version 2: With nav & progress bar
  console.log('\n--- With navigation bar ---');
  const navScreens = await captureSlides('nav', false);
  const navOutputPath = resolve(__dirname, 'pitch_presentation_nav.pdf');
  await savePdf(navScreens, navOutputPath);
  console.log(`PDF saved to: ${navOutputPath}`);
  await browser.close();
}

main().catch(err => {
  console.error('Export failed:', err);
  process.exit(1);
});
