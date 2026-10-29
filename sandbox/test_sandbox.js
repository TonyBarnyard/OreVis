// Headless smoke test for the sandbox: node sandbox/test_sandbox.js [three.min.js path]
// Needs Playwright. Serves this folder, loads the page, evolves through the stages,
// asks the stage 4 robot to tidy up and checks every block ends in its own bin.
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const dir = __dirname, threeLocal = process.argv[2];
const server = http.createServer((req, res) => {
  const f = path.join(dir, decodeURIComponent(req.url.split('?')[0]).replace(/^\/$/, '/index.html'));
  fs.readFile(f, (e, data) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'Content-Type': f.endsWith('.js') ? 'application/javascript' : f.endsWith('.json') ? 'application/json' : f.endsWith('.txt') ? 'text/plain' : 'text/html; charset=utf-8' }); res.end(data); });
}).listen(0);
(async () => {
  const port = server.address().port, errors = [];
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  if (threeLocal) await page.route('**/three.min.js', r => r.fulfill({ path: path.resolve(threeLocal), contentType: 'application/javascript' }));
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(`http://localhost:${port}/index.html`);
  await page.waitForFunction(() => window.__robot);
  const shots = process.env.SHOTS;
  let ok = true;
  const check = (name, cond, extra) => { console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? '  ' + extra : '')); ok = ok && cond; };

  // Stage 1 drives
  await page.keyboard.down('KeyW'); await page.waitForTimeout(1500); await page.keyboard.up('KeyW');
  const moved = await page.evaluate(() => Math.hypot(__robot.robot.x + 0.5, __robot.robot.z + 0.3));
  check('stage 1 drives forward', moved > 0.1, (moved * 1000).toFixed(0) + ' mm');
  if (shots) await page.screenshot({ path: shots + '/stage1.png' });

  // Stage 1 cannot pick
  await page.fill('#talk', 'pick up the red block'); await page.press('#talk', 'Enter');
  const refusal = await page.$eval('#log', e => e.innerText);
  check('stage 1 refuses to pick', /can't do that yet/.test(refusal));

  for (const st of [2, 3, 4]) { await page.click(`.stage[data-stage="${st}"]`); await page.waitForTimeout(400); }
  await page.click('#b-reset'); await page.waitForTimeout(2500);
  if (shots) await page.screenshot({ path: shots + '/stage4.png' });
  await page.fill('#talk', 'tidy up'); await page.press('#talk', 'Enter');
  const t0 = Date.now(); let done = false, lastTask = '';
  while (Date.now() - t0 < 240000) {
    await page.waitForTimeout(2000);
    const s = await page.evaluate(() => ({ task: __robot.task(), held: !!__robot.robot.held, log: document.getElementById('log').innerText.split('\n').slice(-1)[0] }));
    if (s.task !== lastTask) { console.log('   ', ((Date.now() - t0) / 1000).toFixed(0) + 's', s.task, s.held ? '(holding)' : '', '|', s.log); lastTask = s.task; }
    if (shots && !done && s.held) { await page.screenshot({ path: shots + '/carry.png' }); }
    if (/All tidy|can't reach/.test(s.log)) { done = /All tidy/.test(s.log); break; }
  }
  check('stage 4 tidies every block into its bin', done);
  if (shots) await page.screenshot({ path: shots + '/tidy.png' });

  // A 400 g humanoid hand should tip the small walker over
  await page.click('#b-reset'); await page.selectOption('#hand', 'amazing_hand'); await page.waitForTimeout(300);
  await page.fill('#talk', 'pick up the blue block'); await page.press('#talk', 'Enter');
  const t1 = Date.now(); let tipped = false;
  while (Date.now() - t1 < 60000) { await page.waitForTimeout(1500); const l = await page.$eval('#log', e => e.innerText); if (/tipped over|can't lift|can't do that/i.test(l)) { tipped = true; break; } }
  check('Amazing Hand on the stage 4 body is flagged (tips or too heavy)', tipped);

  // Pollen's Amazing Hand: hand lab loads the real model, poses animate, and it mounts on the arm
  const hl = await page.evaluate(() => __robot.hand());
  check('Pollen hand model loads in the hand lab', hl.state === 'ready');
  await page.click('#handPoses [data-pose="point"]'); await page.waitForTimeout(1500);
  const hp = await page.evaluate(() => __robot.hand());
  check('hand lab moves to Pollen\'s point pose', hp.pose === 'point' && hp.t > 0.9, JSON.stringify(hp));
  await page.click('#b-fitHand'); await page.waitForTimeout(800);
  check('Amazing Hand mounts on the robot arm', (await page.evaluate(() => __robot.hand())).onRobot);
  if (shots) { await page.locator('#hand-h').scrollIntoViewIfNeeded(); await page.screenshot({ path: shots + '/handlab.png' }); }

  check('no page errors', errors.length === 0, errors.join(' | '));
  await browser.close(); server.close();
  process.exit(ok ? 0 : 1);
})();
