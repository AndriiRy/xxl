const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1340,height:800},deviceScaleFactor:2});const errs=[];p.on('pageerror',e=>errs.push(e.message));
 await p.goto('http://localhost:8011/');await p.waitForTimeout(2000);await p.click('text=Наводка');await p.waitForTimeout(300);
 await p.locator('#mnt').selectOption('floor');await p.waitForTimeout(1500);
 await p.click('text=Точка +');await p.waitForTimeout(1500);await p.locator('#meas').evaluate(e=>e.scrollIntoView());await p.screenshot({path:'ui3.png'});console.log(errs);await b.close();})();
