'use strict';
let graphCase='example',graphQuery='',graphSource='';
async function showGraph(){
  const route=graphCase==='example'?'/api/graph?case=example':graphCase==='village'?'/api/graph?case=village':'/api/graph?q='+encodeURIComponent(graphQuery)+'&source='+encodeURIComponent(graphSource);
  const data=await api(route),generation=state.request;
  if(generation!==state.request)return;
  let cursor=Math.min(5,data.records.length),hideInherited=false,space=null,spaceWanted=matchMedia('(min-width: 700px)').matches,replayTimer=null;
  const title=data.title;
  const description=data.description;
  content.innerHTML=`<section class="graph-intro"><div><p class="graph-kicker">Swarm Evidence Lab</p><h1>${esc(title)}</h1><p>${esc(description)}</p></div><a href="/demo.html" class="graph-film">Watch the 40-second film</a></section>
    <div class="case-picker"><span>Explore a story</span><div class="graph-cases"><button data-case="example" class="${graphCase==='example'?'active':''}">A completion claim</button><button data-case="wiki" ${state.hosted?'hidden':''} class="${graphCase==='wiki'?'active':''}">A link gets copied</button><button data-case="village" ${state.hosted?'hidden':''} class="${graphCase==='village'?'active':''}">An agent says it is done</button><button data-case="demo" class="${graphCase==='demo'?'active':''}">A shared link example</button></div></div>
    <section class="conversation-map"><div class="map-toolbar"><div><strong>The conversation, connected</strong><span>Click a message to read its source.</span></div><div class="map-view-buttons"><button id="space-toggle" aria-pressed="false">3D view</button><button id="reset-space" hidden>Reset view</button><button id="replay-exchange">Replay</button></div></div><div id="graph-space" hidden></div><div class="map-scroll"><div id="message-map"><svg id="message-links" aria-hidden="true"></svg><div id="message-nodes"></div></div></div><div class="map-summary" id="map-summary"></div></section>
    <div class="trail-time"><span>Move through time</span><input id="trail-time" type="range" min="${data.records.length?1:0}" max="${data.records.length}" value="${cursor}" aria-label="Messages shown in time order"><span id="trail-date"></span><button id="show-all">Show all</button></div>
    <section class="what-we-see"><div><span class="observation-icon">+</span><h2>What the records show</h2><p id="case-finding"></p></div><div><span class="observation-icon uncertain-icon">?</span><h2>What we still need</h2><p>${graphCase==='example'?'A file, a creation log, and evidence that the team received access. This example contains no proof of completion.':esc(data.limits)}</p></div></section>
    <details class="map-your-own"><summary>Follow your own phrase or link</summary><p>Search the available ${state.hosted?'invented examples':'local datasets'}. The map shows exact text matches and the links they contain.</p><form id="graph-search"><input id="graph-query" maxlength="500" aria-label="Phrase or link to follow" placeholder="Paste a link or type a distinctive phrase" value="${esc(graphQuery)}"><button>Find its trail</button></form></details>
    <div class="graph-bottom"><p>${esc(data.scope)}</p><label ${data.edges.some(e=>e.kind.includes('inherited'))?'':'hidden'}><input type="checkbox" id="hide-inherited"> Hide copied links</label><button id="export-graph">Download this graph</button></div>`;
  const map=document.querySelector('#message-map'),nodesRoot=document.querySelector('#message-nodes'),svg=document.querySelector('#message-links');
  const short=x=>String(x||'Unknown').split(' (')[0];
  const relation=kind=>({'recorded label':'posted','same thread':'in this thread','explicit reference':'includes this link','inherited reference':'link carried over','added or replaced lines':'link in changed text','present in available record':'link is present','response to request':'responds to this request','revision of':'next saved revision'}[kind]||kind);
  function currentEdges(){const keys=new Set(data.records.slice(0,cursor).map(r=>r.key));return data.edges.filter(e=>keys.has(e.record_key)&&(!hideInherited||!e.kind.includes('inherited')));}
  function openNode(id){
    const node=data.nodes.find(n=>n.id===id);if(!node)return;
    const r=node.record;
    if(r&&!data.curated){openRecord(r.key);return;}
    document.querySelector('#record-content').innerHTML=r?`<p class="graph-kicker">${data.synthetic?'Invented example record':'Inside this message'}</p><h2>${esc(short(r.actor))}</h2><p class="inspector-time">${esc(date(r.time))}</p><p class="inspector-text">${esc(r.text)}</p><p class="inspector-note">${esc(r.meta.summary)}</p>${r.url?`<p>${link(r.url,'Open the original source')}</p>`:''}<details><summary>Source details</summary><p>${esc(r.key)}</p><p>${esc(r.meta.identity)}</p></details>`:`<p class="graph-kicker">${node.type==='label'?'Name in the records':'Source or reference'}</p><h2>${esc(short(node.label))}</h2><p>${esc(node.note||'This link appears in the selected records.')}</p>${node.url?`<p>${link(node.url,'Open the source')}</p>`:''}<p>${data.edges.filter(e=>e.from===id||e.to===id).map(e=>`<button class="connected-record" data-key="${esc(e.record_key)}">${esc(relation(e.kind))}: open message</button>`).join('')}</p>`;
    document.querySelector('#record-dialog').showModal();document.querySelectorAll('.connected-record').forEach(b=>b.onclick=()=>{document.querySelector('#record-dialog').close();openNode(b.dataset.key);});
  }
  function connect(){
    if(!map.isConnected)return;
    const box=map.getBoundingClientRect(),edges=currentEdges();
    svg.setAttribute('viewBox',`0 0 ${box.width} ${box.height}`);
    svg.innerHTML=edges.map(e=>{const a=Array.from(nodesRoot.children).find(n=>n.dataset.id===e.from),b=Array.from(nodesRoot.children).find(n=>n.dataset.id===e.to);if(!a||!b)return '';const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect(),right=ar.left<br.left;const x1=(right?ar.right:ar.left)-box.left,y1=ar.top+ar.height/2-box.top,x2=(right?br.left:br.right)-box.left,y2=br.top+br.height/2-box.top,mid=(x1+x2)/2;return `<g class="message-edge ${e.kind.includes('inherited')?'copied':''}"><path d="M${x1} ${y1} C${mid} ${y1} ${mid} ${y2} ${x2} ${y2}"/><text x="${mid}" y="${(y1+y2)/2-10}">${esc(relation(e.kind))}</text></g>`;}).join('');
  }
  function render(){
    const edges=currentEdges(),ids=new Set(edges.flatMap(e=>[e.from,e.to])),visible=data.nodes.filter(n=>ids.has(n.id));
    space?.update(edges,data.records.slice(0,cursor).map(r=>r.key));
    const height=Math.max(460,cursor*250+50);map.style.height=height+'px';
    const positions=new Map();
    for(const [type,x] of [['label',12],['record',48],['action',48],['reference',86]]){const list=visible.filter(n=>n.type===type);list.forEach((n,i)=>positions.set(n.id,{x,y:35+(i+.5)*(height-65)/Math.max(1,list.length)}));}
    nodesRoot.innerHTML=visible.map(n=>{const p=positions.get(n.id),r=n.record;return r?`<button class="message-node message-card ${n.type==='action'?'action-card':''}" data-id="${esc(n.id)}" data-x="${p.x}" data-y="${p.y}"><span class="message-card-top"><span class="mini-avatar">${esc(short(r.actor).slice(0,1))}</span><strong>${esc(short(r.actor))}</strong><span class="message-label">${data.synthetic?'EXAMPLE':data.curated?'SUMMARY':r.kind?.includes('revision')?'REVISION':'MESSAGE'}</span></span><p>${esc(r.text.slice(0,135))}${r.text.length>135?'...':''}</p><span class="message-card-bottom">${esc(r.time?.slice(11,16)||'Time unknown')}${r.time?' UTC':''} <span>Open source</span></span></button>`:`<button class="message-node ${n.type==='label'?'person-node':'source-node'}" data-id="${esc(n.id)}" data-x="${p.x}" data-y="${p.y}"><span class="node-avatar">${n.type==='label'?esc(short(n.label).slice(0,1)):'↗'}</span><strong>${esc(short(n.label).slice(0,28))}</strong><small>${n.type==='label'?'Name in the logs':'Shared source'}</small></button>`;}).join('');
    nodesRoot.querySelectorAll('[data-id]').forEach(b=>{b.style.left=b.dataset.x+'%';b.style.top=b.dataset.y+'px';b.onclick=()=>openNode(b.dataset.id);});
    document.querySelector('#map-summary').textContent=graphCase==='example'?'Request, plan, completion claim. No tool result or received file is included.':`${cursor} of ${data.total} matching records. Lines describe relationships in the records.`;
    document.querySelector('#trail-date').textContent=cursor?(data.records[cursor-1]?.time?.slice(0,16).replace('T',' ')+' UTC').replace('undefined UTC','Date unknown'):'No messages';
    const inherited=edges.filter(e=>e.kind.includes('inherited')).length;
    document.querySelector('#case-finding').textContent=graphCase==='example'?'These invented messages demonstrate a review of a completion claim. They are not a finding about real agents.':graphCase==='village'?'The chat contains a plan and a completion claim. This selection does not include proof that the shared document exists.':inherited?`${inherited} link appearance${inherited===1?'':'s'} came from preserved text. A later page revision is not automatically a new exchange.`:'The selected records contain the matching phrase or reference. Their dates show available mention order.';
    requestAnimationFrame(connect);
  }
  document.querySelector('#trail-time').oninput=e=>{cursor=Number(e.target.value);render();};document.querySelector('#show-all').onclick=()=>{cursor=data.records.length;document.querySelector('#trail-time').value=cursor;render();};
  document.querySelector('#hide-inherited').onchange=e=>{hideInherited=e.target.checked;render();};
  document.querySelector('#replay-exchange').onclick=()=>{clearInterval(replayTimer);cursor=Math.min(1,data.records.length);document.querySelector('#trail-time').value=cursor;render();replayTimer=setInterval(()=>{if(state.request!==generation||cursor>=data.records.length){clearInterval(replayTimer);return;}cursor++;document.querySelector('#trail-time').value=cursor;render();},1500);};
  document.querySelector('#graph-search').onsubmit=e=>{e.preventDefault();graphCase='search';graphQuery=document.querySelector('#graph-query').value.trim();graphSource='';go('overview');};
  document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>{graphCase=b.dataset.case;graphSource=graphCase==='village'?'ai-village':graphCase==='demo'?'demo':'';graphQuery=graphCase==='wiki'?'42fa1863-3649-4111-961b-95e9cc704b08':graphCase==='demo'?'https://example.org/result/blue':'';go('overview');});
  document.querySelector('#export-graph').onclick=()=>{const edges=currentEdges(),ids=new Set(edges.flatMap(e=>[e.from,e.to]));download('record-graph.json',JSON.stringify({...data,records:data.records.slice(0,cursor),nodes:data.nodes.filter(n=>ids.has(n.id)),edges,shown:cursor,export_scope:'Current view. Source excerpts stay in this downloaded file.'},null,2));};
  const observer=new ResizeObserver(connect);observer.observe(map);
  window.graphCleanup=()=>{observer.disconnect();clearInterval(replayTimer);space?.dispose();};
  async function setSpace(wanted){
    spaceWanted=wanted;
    const root=document.querySelector('#graph-space'),toggle=document.querySelector('#space-toggle'),scroll=document.querySelector('.map-scroll'),reset=document.querySelector('#reset-space');
    if(wanted&&!space){
      toggle.disabled=true;
      try{const module=await import('/graph-space.js');if(generation!==state.request)return;root.hidden=false;space=module.createGraphSpace(root,data,openNode,relation);space.update(currentEdges(),data.records.slice(0,cursor).map(r=>r.key));}
      catch(error){root.replaceChildren();spaceWanted=false;toggle.title='3D is unavailable in this browser. The readable map is available.';}
      finally{toggle.disabled=false;}
    }
    if(generation!==state.request)return;
    root.hidden=!spaceWanted;scroll.hidden=spaceWanted;reset.hidden=!spaceWanted;
    toggle.textContent=spaceWanted?'Read messages':'3D view';toggle.setAttribute('aria-pressed',String(spaceWanted));
    if(spaceWanted)space.resize();else requestAnimationFrame(connect);
  }
  document.querySelector('#space-toggle').onclick=()=>setSpace(!spaceWanted);
  document.querySelector('#reset-space').onclick=()=>space?.reset();
  render();await setSpace(spaceWanted);
}
