'use strict';
// Public mode stores visitor work in that visitor's browser, never a shared database.
const hostedStoreKey='swarm-evidence-lab-demo-v1';
function readHostedStore(){
  try{
    const data=JSON.parse(localStorage.getItem(hostedStoreKey)||'{}');
    return {reviews:Array.isArray(data.reviews)?data.reviews:[],experiments:Array.isArray(data.experiments)?data.experiments:[]};
  }catch{return {reviews:[],experiments:[]};}
}
function writeHostedStore(data){
  try{localStorage.setItem(hostedStoreKey,JSON.stringify(data));}
  catch{throw Error('This browser cannot save more data. Export your work or use the local app.');}
}
async function hostedAPI(path,body,send){
  const url=new URL(path,location.origin),store=readHostedStore();
  if(url.pathname==='/api/reviews'){
    if(!body)return store.reviews;
    const saved=await send('/api/review/check',body);
    store.reviews=[saved,...store.reviews.filter(x=>x.id!==saved.id)];
    writeHostedStore(store);
    return saved;
  }
  if(url.pathname==='/api/experiments'){
    if(!body)return [...await send(path),...store.experiments.map(x=>({id:x.id,kind:x.kind}))];
    const saved=await send('/api/experiment/check',body);
    store.experiments.push({...body,...saved});
    writeHostedStore(store);
    return saved;
  }
  if(['/api/cooperation','/api/audit','/api/hybrid'].includes(url.pathname)){
    const kind=url.pathname.split('/').pop(),saved=store.experiments.find(x=>x.id===url.searchParams.get('id')&&x.kind===kind);
    if(saved){
      const result=await send('/api/calculate',{kind,records:saved.records,budget:url.searchParams.get('budget')||5,selectivity:url.searchParams.get('selectivity')||10});
      result.dataset={name:saved.name,synthetic:saved.synthetic,description:saved.description};
      return result;
    }
  }
  const result=await send(path,body);
  if(url.pathname==='/api/summary')result.reviews=store.reviews.length;
  return result;
}
