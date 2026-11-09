const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
for(const [n,w,h] of [['tab',1340,800],['phone',390,844]]){
 const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:2});
 const errs=[];p.on('pageerror',e=>errs.push(e.message));
 await p.goto('http://localhost:8011/');await p.waitForTimeout(2500);
 if(n=='tab'){await p.click('text=Наводка');await p.click('text=Замер');await p.waitForTimeout(1500);}
 await p.screenshot({path:`ui_${n}.png`});
 if(n=='tab'){await p.click('text=3200 >> nth=0').catch(()=>{});await p.waitForTimeout(1200);await p.screenshot({path:'ui_sheet.png'});}
 console.log(n,errs);}
await b.close();})();
