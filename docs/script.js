/* ===========================================================================
   Viagens Espaciais — site narrativo interativo
   Estrelas animadas + scrollytelling + galeria + visualizador 3D (Three.js)
   =========================================================================== */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

/* ---------- 1. campo de estrelas animado (canvas) ---------- */
(function starfield(){
  const cv = document.getElementById('sky');
  const ctx = cv.getContext('2d');
  let w, h, stars;
  function resize(){
    w = cv.width = innerWidth; h = cv.height = innerHeight;
    const n = Math.min(320, Math.floor(w * h / 6000));
    stars = Array.from({length:n}, () => ({
      x:Math.random()*w, y:Math.random()*h,
      r:Math.random()*1.4+0.2, a:Math.random(), s:Math.random()*0.02+0.004,
      c: Math.random()>0.85 ? '#bfe4ff' : '#ffffff'
    }));
  }
  function tick(){
    ctx.clearRect(0,0,w,h);
    for(const st of stars){
      st.a += st.s; const tw = 0.5 + 0.5*Math.sin(st.a);
      ctx.globalAlpha = 0.25 + 0.75*tw;
      ctx.fillStyle = st.c;
      ctx.beginPath(); ctx.arc(st.x, st.y, st.r, 0, 7); ctx.fill();
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(tick);
  }
  addEventListener('resize', resize); resize(); tick();
})();

/* ---------- 2. navbar + parallax do hero ---------- */
const nav = document.querySelector('nav');
const heroBg = document.querySelector('.hero .bg');
addEventListener('scroll', () => {
  const y = scrollY;
  nav.classList.toggle('scrolled', y > 60);
  if (heroBg) heroBg.style.transform = `translateY(${y * 0.35}px) scale(1.05)`;
}, {passive:true});

/* ---------- 3. scroll reveal ---------- */
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => { if (e.isIntersecting){ e.target.classList.add('visible'); io.unobserve(e.target); } });
}, {threshold:0.18});
document.querySelectorAll('.reveal').forEach(el => io.observe(el));

/* ---------- 4. galeria + filtros + lightbox ---------- */
const ITEMS = [
  {f:"geral",   img:"prints/01_hero.png",            t:"Vista geral da missão",    c:"Frota de aranhas-exploradoras na superfície lunar com a Terra ao fundo."},
  {f:"geral",   img:"prints/02_panorama.png",        t:"Panorâmica do sítio",      c:"Relevo lunar com crateras, pedras e a frota — escala do ambiente."},
  {f:"robo",    img:"prints/03_robo_heroi.png",      t:"Aranha-exploradora",       c:"Robô-explorador autoral em close, com profundidade de campo."},
  {f:"robo",    img:"prints/04_robo_lateral.png",    t:"Pernas hexápodes",         c:"Seis pernas arqueadas de três segmentos (coxa, fêmur, tíbia)."},
  {f:"robo",    img:"prints/05_robo_visor.png",      t:"Cabeça-sensor",            c:"Cluster de olhos cyan, faróis e sonda do explorador."},
  {f:"satelite",img:"prints/06_satelite.png",        t:"Satélite de comunicação",  c:"Satélite autoral em órbita, com a Terra ao fundo."},
  {f:"satelite",img:"prints/07_satelite_paineis.png",t:"Painéis solares & antena", c:"Células solares procedurais e antena parabólica."},
  {f:"foguete", img:"prints/08_foguete.png",         t:"Foguete-lander",           c:"Nave de origem: corpo de foguete, nariz cônico, aletas e estágio dourado."},
  {f:"foguete", img:"prints/09_foguete_detalhe.png", t:"Estágio de descida",       c:"Pernas de pouso, tanques e bocal do motor em detalhe."},
  {f:"foguete", img:"prints/10_bandeira.png",        t:"Bandeira do Brasil",       c:"Marco da missão fincado no solo, com o foguete ao fundo."},
  {f:"caverna", img:"prints/11_caverna.png",         t:"A boca da caverna",        c:"Poço com arco de rochas e brilho interno, inspecionado por uma aranha."},
  {f:"terra",   img:"prints/12_terra.png",           t:"A Terra vista da Lua",     c:"Nuvens, atmosfera e luzes de cidade — shader procedural."},
  {f:"geral",   img:"prints/13_orbital_topo.png",    t:"Vista orbital",            c:"Disposição geral dos elementos vista de cima."},
  {f:"model",   img:"prints/14_wireframe_cena.png",  t:"Wireframe da cena",        c:"Malha poligonal de todo o ambiente — prova da modelagem autoral."},
  {f:"model",   img:"prints/15_clay_robo.png",       t:"Render clay",              c:"Forma e volume do robô sem materiais — estudo de silhueta."},
  {f:"model",   img:"prints/16_wireframe_robo.png",  t:"Wireframe do robô",        c:"Detalhe da malha do robô, mostrando a construção."},
  // --- breakdown por objeto (final / clay / wireframe) ---
  {f:"model",   img:"prints/modelagem/aranha_final.png",    t:"Aranha — final",      c:"Aranha-exploradora isolada, com materiais."},
  {f:"model",   img:"prints/modelagem/aranha_clay.png",     t:"Aranha — clay",       c:"Volume da aranha sem materiais."},
  {f:"model",   img:"prints/modelagem/aranha_wire.png",     t:"Aranha — wireframe",  c:"Malha poligonal da aranha-exploradora."},
  {f:"model",   img:"prints/modelagem/foguete_final.png",   t:"Foguete — final",     c:"Foguete-lander isolado, com materiais."},
  {f:"model",   img:"prints/modelagem/foguete_clay.png",    t:"Foguete — clay",      c:"Volume do foguete sem materiais."},
  {f:"model",   img:"prints/modelagem/foguete_wire.png",    t:"Foguete — wireframe", c:"Malha poligonal do foguete-lander."},
  {f:"model",   img:"prints/modelagem/satelite_final.png",  t:"Satélite — final",    c:"Satélite isolado, com materiais."},
  {f:"model",   img:"prints/modelagem/satelite_clay.png",   t:"Satélite — clay",     c:"Volume do satélite sem materiais."},
  {f:"model",   img:"prints/modelagem/satelite_wire.png",   t:"Satélite — wireframe",c:"Malha poligonal do satélite."},
  {f:"model",   img:"prints/modelagem/bandeira_final.png",  t:"Bandeira — final",    c:"Bandeira do Brasil isolada, com materiais."},
  {f:"model",   img:"prints/modelagem/bandeira_clay.png",   t:"Bandeira — clay",     c:"Volume da bandeira sem materiais."},
  {f:"model",   img:"prints/modelagem/bandeira_wire.png",   t:"Bandeira — wireframe",c:"Malha da bandeira do Brasil."},
];
const TAGS={geral:"Visão Geral",robo:"Aranhas",foguete:"Foguete",satelite:"Satélite",caverna:"Caverna",terra:"Terra",model:"Modelagem"};
const grid = document.getElementById('grid');
ITEMS.forEach((it,i)=>{
  const fig=document.createElement('figure');
  fig.className='card';fig.dataset.f=it.f;
  fig.innerHTML=`<img loading="lazy" src="${it.img}" alt="${it.t}">
    <div class="meta"><div class="tag">${TAGS[it.f]}</div><div class="t">${it.t}</div></div>`;
  fig.addEventListener('click',()=>openLB(i));
  grid.appendChild(fig);
});
document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  const f=b.dataset.f;
  document.querySelectorAll('.card').forEach(c=>c.classList.toggle('hide', f!=='all' && c.dataset.f!==f));
}));
const lb=document.getElementById('lb'),lbimg=document.getElementById('lbimg'),lbcap=document.getElementById('lbcap');
let cur=0;
function openLB(i){cur=i;renderLB();lb.classList.add('open');}
function renderLB(){const it=ITEMS[cur];lbimg.src=it.img;lbcap.innerHTML=`<b>${it.t}</b> — ${it.c}`;}
function step(d){cur=(cur+d+ITEMS.length)%ITEMS.length;renderLB();}
document.getElementById('lbx').onclick=()=>lb.classList.remove('open');
document.getElementById('lbprev').onclick=e=>{e.stopPropagation();step(-1);};
document.getElementById('lbnext').onclick=e=>{e.stopPropagation();step(1);};
lb.addEventListener('click',e=>{if(e.target===lb)lb.classList.remove('open');});
addEventListener('keydown',e=>{
  if(!lb.classList.contains('open'))return;
  if(e.key==='Escape')lb.classList.remove('open');
  if(e.key==='ArrowLeft')step(-1);
  if(e.key==='ArrowRight')step(1);
});

/* ---------- 5. visualizador 3D da aranha (Three.js) ---------- */
(function viewer3d(){
  const host = document.getElementById('viewer3d');
  const loaderEl = host.querySelector('.loader');
  const renderer = new THREE.WebGLRenderer({antialias:true, alpha:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(3.4, 1.8, 4.4);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  scene.add(new THREE.HemisphereLight(0xbcd6ff, 0x202840, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(4,6,4); scene.add(key);
  const rim = new THREE.DirectionalLight(0x66aaff, 1.4); rim.position.set(-5,2,-4); scene.add(rim);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.autoRotate = true; controls.autoRotateSpeed = 1.4;
  controls.enablePan = false; controls.minDistance = 2.2; controls.maxDistance = 9;

  function resize(){
    const w = host.clientWidth, h = host.clientHeight;
    renderer.setSize(w,h,false);
    camera.aspect = w/h; camera.updateProjectionMatrix();
  }
  addEventListener('resize', resize); resize();

  const MODEL_URL = (typeof window !== 'undefined' && window.SPIDER_GLB) ? window.SPIDER_GLB : 'models/spider.glb';
  new GLTFLoader().load(MODEL_URL, (gltf)=>{
    const obj = gltf.scene;
    const box = new THREE.Box3().setFromObject(obj);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    obj.position.sub(center);                       // centraliza
    const scale = 3.0 / Math.max(size.x, size.y, size.z);
    obj.scale.setScalar(scale);
    obj.position.multiplyScalar(scale);
    obj.position.y += 0.2;
    scene.add(obj);
    controls.target.set(0,0,0);
    if (loaderEl) loaderEl.remove();
  }, undefined, (err)=>{
    if (loaderEl) loaderEl.innerHTML = '⚠️ Não foi possível carregar o modelo 3D (precisa de internet para o Three.js).';
    console.error(err);
  });

  (function loop(){
    requestAnimationFrame(loop);
    controls.update();
    renderer.render(scene, camera);
  })();
})();
