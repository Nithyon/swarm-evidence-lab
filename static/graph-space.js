import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';

// Positions are a visual layout. Connections come only from the supplied graph.
export function createGraphSpace(root, data, openNode, relation) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#fffff8');
  const camera = new THREE.PerspectiveCamera(42, 1, .1, 100);
  camera.position.set(0, 1, 10);
  const renderer = new THREE.WebGLRenderer({antialias:true, alpha:false});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute('aria-label','3D map of recorded connections. Use the message buttons to open sources.');
  root.append(renderer.domElement);
  const labels = document.createElement('div'); labels.className = 'space-labels'; root.append(labels);
  const hint = document.createElement('div'); hint.className = 'space-hover'; hint.textContent = 'Drag to rotate. Scroll to zoom. Click a name or message to open its source.';
  root.append(hint);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8d9cac, 3));
  const light = new THREE.DirectionalLight(0xffffff, 3); light.position.set(4, 7, 5); scene.add(light);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0,-.5,0);
  controls.enableDamping = true; controls.dampingFactor = .09;
  controls.minDistance = 5; controls.maxDistance = 22;
  controls.maxPolarAngle = Math.PI * .82;
  const grid = new THREE.GridHelper(24, 36, 0xdde1dc, 0xe7e9e1);
  grid.position.y = -2.65;
  grid.material.transparent = true; grid.material.opacity = .42; scene.add(grid);
  const colors = {label:0x53778b,record:0xc68e62,action:0xc68e62,reference:0x749b83};
  const meshes = new Map(), edgeMeshes = [], resources = [];
  const groups = ['label','record','action','reference'];
  for (const type of groups) {
    const list = data.nodes.filter(n=>n.type===type);
    list.forEach((node,i)=>{
      const x = type==='label'?-2.85:type==='reference'?2.9:0;
      const y = list.length<=1?.25:1.55-i*3.1/Math.max(1,list.length-1);
      const z = type==='record'||type==='action'? .55 + (i%2)*.65 : (i%2)*.35-.35;
      const geometry = type==='reference'?new THREE.OctahedronGeometry(.24,0):type==='label'?new THREE.SphereGeometry(.22,24,16):new THREE.BoxGeometry(.38,.28,.16);
      const material = new THREE.MeshStandardMaterial({color:colors[type],roughness:.34,metalness:.12});
      resources.push(geometry,material);
      const mesh = new THREE.Mesh(geometry,material); mesh.position.set(x,y,z); mesh.userData.node = node;
      scene.add(mesh);
      const button = document.createElement('button'); button.className = 'space-label '+type;
      const title = document.createElement('strong');
      title.textContent = String(node.record?node.record.actor:node.label).split(' (')[0].slice(0,44);
      const subtitle = document.createElement('small');
      subtitle.textContent = node.record?'Open '+(data.synthetic?'invented record':data.curated?'message summary':'source record'):type==='label'?'Name in the records':'Source or reference';
      button.append(title,subtitle); button.onclick = ()=>openNode(node.id); labels.append(button);
      meshes.set(node.id,{mesh,button});
    });
  }
  for (const edge of data.edges) {
    const a = meshes.get(edge.from)?.mesh.position, b = meshes.get(edge.to)?.mesh.position;
    if (!a || !b) continue;
    const midpoint = a.clone().add(b).multiplyScalar(.5); midpoint.z += .5;
    const curve = new THREE.QuadraticBezierCurve3(a,midpoint,b);
    const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(40));
    const copied = edge.kind.includes('inherited');
    const material = copied?new THREE.LineDashedMaterial({color:0xb79870,dashSize:.12,gapSize:.08,transparent:true,opacity:.7}):new THREE.LineBasicMaterial({color:0x8baca6,transparent:true,opacity:.78});
    const line = new THREE.Line(geometry,material); line.userData.edge = edge;
    if (copied) line.computeLineDistances(); scene.add(line); edgeMeshes.push(line); resources.push(geometry,material);
  }
  const raycaster = new THREE.Raycaster(); raycaster.params.Line.threshold = .09;
  const pointer = new THREE.Vector2(), projected = new THREE.Vector3();
  let alive = true, dirty = true, width = 1, height = 1, frame = 0, highlighted = null, down = null;
  function resize() {
    width = root.clientWidth || 1; height = root.clientHeight || 1;
    renderer.setSize(width,height); camera.aspect = width/height; camera.updateProjectionMatrix(); dirty = true;
  }
  function hit(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
    raycaster.setFromCamera(pointer,camera);
    return raycaster.intersectObjects([...meshes.values()].map(n=>n.mesh).filter(n=>n.visible).concat(edgeMeshes.filter(e=>e.visible)))[0]?.object;
  }
  function hover(event) {
    const found = hit(event);
    if (highlighted) highlighted.scale.setScalar(1);
    highlighted = found?.userData.node?found:null;
    if (highlighted) highlighted.scale.setScalar(1.25);
    const n = found?.userData.node, e = found?.userData.edge;
    hint.textContent = n?String(n.record?n.record.text:n.note||n.label).slice(0,170):e?relation(e.kind)+' — open its message for the evidence.':'Drag to rotate. Scroll to zoom. Click a name or message to open its source.';
    renderer.domElement.style.cursor = n||e?'pointer':'grab'; dirty = true;
  }
  function pointerDown(e){down={x:e.clientX,y:e.clientY};}
  function pointerUp(e){if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>5)return;const found=hit(e);if(found?.userData.node)openNode(found.userData.node.id);else if(found?.userData.edge)openNode(found.userData.edge.record_key);down=null;}
  renderer.domElement.addEventListener('pointermove',hover);
  renderer.domElement.addEventListener('pointerdown',pointerDown);
  renderer.domElement.addEventListener('pointerup',pointerUp);
  controls.addEventListener('change',()=>{dirty=true;});
  const observer = new ResizeObserver(resize); observer.observe(root); resize();
  function draw() {
    if (!alive || !root.isConnected) return;
    if (root.getClientRects().length && !document.hidden) {
      if (controls.update()) dirty = true;
      if (dirty) {
        renderer.render(scene,camera);
        meshes.forEach(({mesh,button})=>{
          projected.copy(mesh.position).project(camera);
          const inFrame = mesh.visible && projected.z>=-1 && projected.z<=1 && Math.abs(projected.x)<1.15 && Math.abs(projected.y)<1.1;
          button.hidden = !inFrame;
          if(inFrame){button.style.left=((projected.x+1)*width/2)+'px';button.style.top=((-projected.y+1)*height/2+20)+'px';}
        });
        dirty = false;
      }
    }
    frame = requestAnimationFrame(draw);
  }
  draw();
  return {
    update(edges, recordKeys) {
      const ids = new Set(edges.flatMap(e=>[e.from,e.to])); recordKeys.forEach(k=>ids.add(k));
      meshes.forEach(({mesh})=>{mesh.visible=ids.has(mesh.userData.node.id);});
      for(const type of groups){
        const visible=[...meshes.values()].filter(n=>n.mesh.visible&&n.mesh.userData.node.type===type);
        visible.forEach(({mesh},i)=>{
          const row=i%5, layer=Math.floor(i/5), rows=Math.min(5,visible.length);
          mesh.position.y=rows<=1?.25:1.6-row*3.2/(rows-1);
          mesh.position.z=((type==='record'||type==='action') ? .55 : 0)-layer*1.3;
        });
      }
      edgeMeshes.forEach(line=>{line.visible=edges.includes(line.userData.edge);}); dirty=true;
      edgeMeshes.filter(line=>line.visible).forEach(line=>{
        const edge=line.userData.edge,a=meshes.get(edge.from).mesh.position,b=meshes.get(edge.to).mesh.position;
        const mid=a.clone().add(b).multiplyScalar(.5);mid.z+=.5;
        line.geometry.setFromPoints(new THREE.QuadraticBezierCurve3(a,mid,b).getPoints(40));
        line.geometry.computeBoundingSphere();
        if(edge.kind.includes('inherited'))line.computeLineDistances();
      });
    },
    reset(){camera.position.set(0,1,10);controls.target.set(0,-.5,0);controls.update();dirty=true;},
    resize,
    dispose(){alive=false;cancelAnimationFrame(frame);observer.disconnect();controls.dispose();resources.forEach(r=>r.dispose());grid.geometry.dispose();grid.material.dispose();renderer.dispose();renderer.forceContextLoss();root.replaceChildren();}
  };
}
