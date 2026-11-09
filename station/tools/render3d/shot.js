const {chromium} = require('playwright');
(async () => { const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader']}); const p = await b.newPage({viewport: {width: 900, height: 800}, deviceScaleFactor: 1});
 p.on('pageerror', e => console.log('ERR', e.message)); p.on('console', m => console.log(m.text()));
 for (const [n, q] of [['a', 'v=0&az=-60&el=20'], ['b', 'v=-90&az=35&el=12'], ['c', 'v=30&az=120&el=25'], ['d', 'v=0&az=-90&el=-25']]) {
  await p.goto('http://localhost:8123/index.html?' + q); await p.waitForFunction(() => document.title == 'done', null, {timeout: 120000}); await p.screenshot({path: n + '.png'}); }
 await b.close(); })();
