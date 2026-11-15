/* Mapa geral das estações NEXRAD — visão de localização, não mosaico de dados. */
(() => {
  "use strict";
  const canvas = document.getElementById("overview-map");
  const status = document.getElementById("overview-status");
  const regionBar = document.getElementById("overview-regions");
  if (!canvas || !window.RADARS) return;
  const ctx = canvas.getContext("2d");
  const regions = {
    "EUA": [-127,-65,23,51], "Alasca": [-172,-128,51,72.5],
    "Havaí": [-161.5,-154,18,23], "Caribe": [-83,-60,8,27],
    "Pacífico": [125,180,-5,55], "Mundo": [-180,180,-60,80]
  };
  let region = "EUA", points = [], selected = null, coast = [], states = [];
  const D = Math.PI / 180;
  function decode(topology) {
    const [sx,sy] = topology.transform.scale, [tx,ty] = topology.transform.translate;
    return topology.arcs.map(arc => {
      let x=0,y=0;
      return arc.map(p => { x+=p[0]; y+=p[1]; return [x*sx+tx,y*sy+ty]; });
    });
  }
  Promise.all([
    fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json").then(r=>r.ok?r.json():null),
    fetch("https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json").then(r=>r.ok?r.json():null)
  ]).then(([w,s]) => {
    if (w) coast=decode(w);
    if (s) states=decode(s);
    draw();
  }).catch(() => draw());
  function draw() {
    const dpr=Math.min(window.devicePixelRatio||1,2), W=Math.max(1,Math.round(canvas.clientWidth*dpr)), H=Math.max(1,Math.round(canvas.clientHeight*dpr));
    canvas.width=W; canvas.height=H;
    const [x0,x1,y0,y1]=regions[region], mid=(y0+y1)/2, cs=Math.max(.25,Math.cos(mid*D));
    const sx=W/((x1-x0)*cs), sy=H/(y1-y0), scale=Math.min(sx,sy)*.94;
    const ox=(W-(x1-x0)*cs*scale)/2, oy=(H-(y1-y0)*scale)/2;
    const X=lon=>ox+(lon-x0)*cs*scale, Y=lat=>oy+(y1-lat)*scale;
    ctx.fillStyle="#07111a"; ctx.fillRect(0,0,W,H);
    ctx.strokeStyle="#203744"; ctx.lineWidth=Math.max(1,dpr);
    for(let lon=Math.ceil(x0/10)*10;lon<x1;lon+=10){ctx.beginPath();ctx.moveTo(X(lon),0);ctx.lineTo(X(lon),H);ctx.stroke();}
    for(let lat=Math.ceil(y0/10)*10;lat<y1;lat+=10){ctx.beginPath();ctx.moveTo(0,Y(lat));ctx.lineTo(W,Y(lat));ctx.stroke();}
    function paths(arcs,color,width){ctx.beginPath();for(const arc of arcs)for(let i=0;i<arc.length;i++){const q=arc[i];if(i)ctx.lineTo(X(q[0]),Y(q[1]));else ctx.moveTo(X(q[0]),Y(q[1]));}ctx.strokeStyle=color;ctx.lineWidth=width*dpr;ctx.stroke();}
    if(coast.length)paths(coast,"#78909c",1);
    if(states.length && (region==="EUA"||region==="Alasca"||region==="Havaí"))paths(states,"#344c5a",.65);
    points=[];
    for(const r of window.RADARS){
      const lon=r[3],lat=r[2]; if(lon<x0||lon>x1||lat<y0||lat>y1)continue;
      const x=X(lon),y=Y(lat); points.push({r,x,y});
      // Anel de 230 km meramente ilustrativo; não representa cobertura operacional real.
      const rx=230/111.32*scale, ry=230/111.32*scale;
      ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,Math.PI*2);
      ctx.fillStyle="rgba(0,220,110,.035)";ctx.fill();
      ctx.strokeStyle="rgba(0,220,110,.20)";ctx.lineWidth=1*dpr;ctx.stroke();
      ctx.beginPath();ctx.arc(x,y,r[0]===selected?5*dpr:3*dpr,0,Math.PI*2);
      ctx.fillStyle=r[0]===selected?"#ffd34e":"#00e676";ctx.fill();
      if(region!=="Mundo" && scale>5) {ctx.font=(10*dpr)+"px monospace";ctx.fillStyle="#d8e6ed";ctx.fillText(r[0],x+5*dpr,y-5*dpr);}
    }
    // Eco sintético do modelo ativo, convertido da posição relativa ao radar para coordenadas geográficas.
    const sim = window.RadarSimulatorState && window.RadarSimulatorState();
    if (sim) {
      const stormLat = sim.lat + sim.stormY / 111.32;
      const stormLon = sim.lon + sim.stormX / (111.32 * Math.max(.15, Math.cos(stormLat * D)));
      if (stormLon >= x0 && stormLon <= x1 && stormLat >= y0 && stormLat <= y1) {
        const ex=X(stormLon), ey=Y(stormLat), radius=sim.dbz>=60?29:sim.dbz>=45?24:18;
        const color=sim.dbz>=60?"rgba(235,35,190,0.68)":sim.dbz>=45?"rgba(255,105,20,0.68)":sim.dbz>=30?"rgba(255,220,35,0.65)":"rgba(45,190,90,0.58)";
        ctx.save(); ctx.translate(ex,ey); ctx.rotate(-.28);
        ctx.beginPath();
        for(let i=0;i<=48;i++){
          const a=i/48*Math.PI*2, wobble=1+.13*Math.sin(3*a)+.08*Math.cos(5*a);
          const px=Math.cos(a)*radius*wobble/111.32*scale;
          const py=Math.sin(a)*radius*wobble/111.32*scale;
          if(i===0)ctx.moveTo(px,py);else ctx.lineTo(px,py);
        }
        ctx.closePath();ctx.fillStyle=color;ctx.fill();
        ctx.strokeStyle="rgba(255,255,255,.8)";ctx.lineWidth=1.2*dpr;ctx.stroke();
        if(sim.rotation){ctx.beginPath();ctx.arc(0,0,5*dpr,0,Math.PI*2);ctx.strokeStyle="#fff";ctx.lineWidth=1.5*dpr;ctx.stroke();}
        ctx.restore();
        ctx.font="bold "+(10*dpr)+"px monospace";ctx.fillStyle="#fff";
        ctx.fillText("ECO SIMULADO · "+Math.round(sim.dbz)+" dBZ",ex+8*dpr,ey-9*dpr);
      }
    }
    status.textContent=points.length+" estações nesta região · eco sintético acompanha a tempestade do radar individual · não é mosaico de dados observados.";
  }
  regionBar.innerHTML=Object.keys(regions).map(k=>'<button type="button" data-region="'+k+'"'+(k===region?' aria-pressed="true"':'')+'>'+k+'</button>').join("");
  regionBar.addEventListener("click",e=>{const b=e.target.closest("button[data-region]");if(!b)return;region=b.dataset.region;regionBar.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));draw();});
  canvas.addEventListener("pointermove",e=>{
    const rect=canvas.getBoundingClientRect(),k=canvas.width/rect.width,x=(e.clientX-rect.left)*k,y=(e.clientY-rect.top)*k;
    let best=null,dist=14*k;for(const p of points){const d=Math.hypot(p.x-x,p.y-y);if(d<dist){dist=d;best=p;}}
    canvas.style.cursor=best?"pointer":"default";
    if(best)status.textContent=best.r[0]+" — "+best.r[1]+" · "+best.r[2].toFixed(3)+"°, "+best.r[3].toFixed(3)+"°";
  });
  canvas.addEventListener("click",e=>{
    const rect=canvas.getBoundingClientRect(),k=canvas.width/rect.width,x=(e.clientX-rect.left)*k,y=(e.clientY-rect.top)*k;
    let best=null,dist=14*k;for(const p of points){const d=Math.hypot(p.x-x,p.y-y);if(d<dist){dist=d;best=p;}}
    if(best){selected=best.r[0];draw();status.textContent=best.r[0]+" — "+best.r[1]+" identificado no mapa. Use “Escolher radar” para carregar esta estação no radar individual.";}
  });
  if(typeof ResizeObserver!=="undefined")new ResizeObserver(draw).observe(canvas);else window.addEventListener("resize",draw);
  draw();
  window.setInterval(draw, 1000);
})();