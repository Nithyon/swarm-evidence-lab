'use strict';
// Property setters redraw Canvas during deterministic seeks with callbacks suppressed.
(() => {
const canvas=document.querySelector('#swarm'),ctx=canvas.getContext('2d');
const points=Array.from({length:150},(_,i)=>({x:((i*137+73)%1800)+60,y:((i*239+191)%920)+80,r:1.8+(i%4)*.6,phase:i*.37}));let tick=0;
const painter={get time(){return tick;},set time(t){tick=t;draw(t);}};
function draw(t){ctx.clearRect(0,0,1920,1080);const spread=Math.min(1,Math.max(0,(t-3)/3));const fade=t<10?1:Math.max(.12,1-(t-10)/6);for(let i=0;i<points.length;i++){const p=points[i],cx=1340+Math.cos(p.phase)*220,cy=500+Math.sin(p.phase*1.3)*250;const x=cx*(1-spread)+p.x*spread+Math.sin(t*.35+p.phase)*12,y=cy*(1-spread)+p.y*spread+Math.cos(t*.3+p.phase)*12;if(i%5===0&&t>4&&t<10){const q=points[(i+7)%points.length];ctx.strokeStyle=`rgba(94,132,100,${.12*fade})`;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(q.x,q.y);ctx.stroke();}ctx.fillStyle=`rgba(${i%3?'103,134,105':'165,152,103'},${.46*fade})`;ctx.beginPath();ctx.arc(x,y,p.r,0,Math.PI*2);ctx.fill();}}
document.querySelector('#record-time').textContent='09:03 / INVENTED TIME';
const tl=gsap.timeline({paused:true,defaults:{ease:'power3.inOut'}});tl.to(painter,{time:40,duration:40,ease:'none'},0);
function scene(id,start,end){tl.to(id,{opacity:1,duration:.65},start);if(end<40)tl.to(id,{opacity:0,duration:.55},end-.55);}
scene('#opening',0,5.8);tl.fromTo('#opening h1',{y:70,opacity:0},{y:0,opacity:1,duration:1.25},.3);tl.fromTo('#opening .subcopy',{y:20,opacity:0},{y:0,opacity:1,duration:.7},1.2);tl.to('#opening',{scale:.93,x:-80,duration:1},4.8);
scene('#voices',5.2,11.5);tl.fromTo('#voice-a',{x:170,y:80,scale:.55,opacity:0},{x:0,y:0,scale:1,opacity:1,duration:1.05},5.3);tl.fromTo('#voice-b',{x:-120,y:90,scale:.6,opacity:0},{x:0,y:0,scale:1,opacity:1,duration:1.05},7);tl.to('#voice-a',{y:-35,duration:1},8.8);tl.to('#voice-b',{scale:1.1,x:-180,y:-100,duration:1},10);
scene('#focus',11,18);tl.fromTo('.source-card',{x:230,y:100,scale:.8,opacity:0},{x:0,y:0,scale:1,opacity:1,duration:1.1},11.2);tl.fromTo('.focus-heading',{x:-90,opacity:0},{x:0,opacity:1,duration:.8},11.6);tl.fromTo('.source-meta',{opacity:0,y:10},{opacity:1,y:0,duration:.7},13.5);tl.fromTo('.focus-foot',{opacity:0},{opacity:1,duration:.8},15.2);tl.to('.source-card',{scale:.65,x:-540,y:120,duration:1},17);
scene('#map',17.5,28.5);tl.fromTo('.map-heading',{y:30,opacity:0},{y:0,opacity:1,duration:.7},17.7);
[['#g-request',18],['#g-plan',18.8],['#g-claim',20.1],['#g-evidence',23]].forEach(([id,t])=>tl.fromTo(id,{scale:.6,opacity:0,y:35},{scale:1,opacity:1,y:0,duration:.75},t));
[['#edge-a',18.5],['#edge-b',19.8],['#edge-reply',21],['#edge-link',22.7],['#edge-link-b',23.7]].forEach(([id,t])=>tl.to(id,{strokeDashoffset:0,duration:1.1,ease:'power2.out'},t));
tl.fromTo('#reply-tag',{opacity:0},{opacity:1,duration:.5},21.7);tl.fromTo('#topic-tag',{opacity:0},{opacity:1,duration:.5},24);tl.fromTo('.map-note',{opacity:0},{opacity:1,duration:.8},26);
scene('#reveal',28,34.5);tl.fromTo('#reveal h2',{y:50,opacity:0},{y:0,opacity:1,duration:.8},28.2);tl.fromTo('.three-facts>div',{y:35,opacity:0},{y:0,opacity:1,duration:.7,stagger:.45},29.4);
scene('#ending',34,40);tl.fromTo('#ending h1',{y:55,opacity:0},{y:0,opacity:1,duration:1},34.2);tl.fromTo('.end-link',{y:20,opacity:0},{y:0,opacity:1,duration:.7},35.9);tl.to('#progress-fill',{width:'100%',duration:40,ease:'none'},0);tl.set({}, {},40);
window.__timelines=window.__timelines||{};window.__timelines.trail=tl;
})();
