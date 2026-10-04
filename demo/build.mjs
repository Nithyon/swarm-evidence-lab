import {readFileSync,writeFileSync,copyFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
const root=dirname(fileURLToPath(import.meta.url));
const template=readFileSync(join(root,'scene.html.in'),'utf8');
const script=readFileSync(join(root,'demo.js'),'utf8');
// HyperFrames static validation sees the paused timeline in the entry HTML.
writeFileSync(join(root,'index.html'),template.replace('<script src="./demo.js"></script>',`<script>\n${script}\n</script>`));
writeFileSync(join(root,'../static/demo.html'),template.replace('</body>','<script src="./demo-player.js"></script></body>'));
for(const name of ['demo.css','demo.js','gsap.min.js'])copyFileSync(join(root,name),join(root,'../static',name));

