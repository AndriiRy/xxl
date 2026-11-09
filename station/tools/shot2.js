const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
 const p=await b.newPage({viewport:{width:1340,height:800},deviceScaleFactor:2});const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()=='error')errs.push(m.text())});
 await p.goto('http://localhost:8011/');await p.waitForTimeout(2500);await p.screenshot({path:'ui2_plan.png'});
 await p.click('#t3d');await p.waitForTimeout(800);await p.screenshot({path:'ui2_3d.png'});
 await p.mouse.move(500,400);await p.mouse.down();await p.mouse.move(380,330,{steps:5});await p.mouse.up();await p.waitForTimeout(300);await p.screenshot({path:'ui2_3d_b.png'});
 await p.click('#t2d');await p.locator('#info').evaluate(e=>e.scrollIntoView());
 await p.click('text=S1 A-B стена');await p.waitForTimeout(800);await p.screenshot({path:'ui2_surf.png'});
 console.log(errs);await b.close();})();
