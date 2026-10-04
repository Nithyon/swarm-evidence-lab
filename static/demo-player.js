'use strict';
(() => {if(!/\/demo\.html$/.test(location.pathname))return;
const stage=document.querySelector('#stage'),tl=window.__timelines.trail,play=document.querySelector('#play'),scrub=document.querySelector('#scrub');let running=!matchMedia('(prefers-reduced-motion: reduce)').matches,start=performance.now(),position=0;
document.querySelector('#player').style.display='flex';
function fit(){const s=Math.min(innerWidth/1920,(innerHeight-70)/1080);stage.style.transform=`scale(${s})`;stage.style.left=((innerWidth-1920*s)/2)+'px';stage.style.top=((innerHeight-70-1080*s)/2)+'px';}fit();addEventListener('resize',fit);
function seek(t){position=Math.max(0,Math.min(40,t));tl.seek(position,false);scrub.value=position;document.querySelector('#clock').textContent=`00:${String(Math.floor(position)).padStart(2,'0')} / 00:40`;}
window.__seek=t=>{running=false;play.textContent='Play';seek(t);};play.onclick=()=>{if(position>=40)seek(0);running=!running;start=performance.now();play.textContent=running?'Pause':'Play';};document.querySelector('#replay').onclick=()=>{seek(0);running=true;start=performance.now();play.textContent='Pause';};scrub.oninput=()=>window.__seek(Number(scrub.value));function frame(now){if(running){seek(position+(now-start)/1000);start=now;if(position>=40){running=false;play.textContent='Replay';}}requestAnimationFrame(frame);}seek(0);requestAnimationFrame(frame);
})();
