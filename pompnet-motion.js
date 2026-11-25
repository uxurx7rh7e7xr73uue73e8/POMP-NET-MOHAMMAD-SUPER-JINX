/* POMP NET MOHAMMAD — 24-scene animated background. No external libraries. */
(function(){
 "use strict";
 if(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;
 var scenes=[
  ["#050509","#8b35ff","#168cff"],["#06101c","#22d3ee","#4169e1"],["#100719","#c084fc","#7c3aed"],["#07131a","#34d399","#0ea5e9"],
  ["#100b08","#fb923c","#ef4444"],["#07101a","#93c5fd","#38bdf8"],["#090914","#a78bfa","#ec4899"],["#07140f","#86efac","#22c55e"],
  ["#090d1b","#60a5fa","#818cf8"],["#130b18","#f0abfc","#a855f7"],["#080e14","#67e8f9","#2563eb"],["#14100a","#fbbf24","#f97316"],
  ["#050b13","#38bdf8","#6366f1"],["#110b17","#d8b4fe","#818cf8"],["#071416","#5eead4","#0d9488"],["#100b0b","#fca5a5","#fb7185"],
  ["#080d19","#c4b5fd","#3b82f6"],["#101007","#bef264","#65a30d"],["#0b0916","#e879f9","#8b5cf6"],["#06131b","#7dd3fc","#0ea5e9"],
  ["#140b0a","#fdba74","#dc2626"],["#080f14","#a5f3fc","#0891b2"],["#100b19","#c084fc","#db2777"],["#070b12","#93c5fd","#4f46e5"]
 ];
 var canvas=document.createElement("canvas");canvas.id="pompnet-motion";canvas.setAttribute("aria-hidden","true");
 var ctx=canvas.getContext("2d",{alpha:true});if(!ctx)return;
 var glow=document.createElement("div");glow.className="pn-motion-glow";glow.setAttribute("aria-hidden","true");
 document.documentElement.classList.add("pn-motion-ready");
 document.body.insertBefore(glow,document.body.firstChild);document.body.insertBefore(canvas,document.body.firstChild);
 var w=0,h=0,dpr=1,scene=0,last=0,swap=0,particles=[];
 function resize(){dpr=Math.min(window.devicePixelRatio||1,1.5);w=innerWidth;h=innerHeight;canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);canvas.style.width=w+"px";canvas.style.height=h+"px";ctx.setTransform(dpr,0,0,dpr,0,0);particles=[];var n=Math.min(95,Math.max(35,Math.floor(w*h/15000)));for(var i=0;i<n;i++)particles.push({x:Math.random()*w,y:Math.random()*h,r:.5+Math.random()*2.1,v:.12+Math.random()*.55,p:Math.random()*6.28,a:.12+Math.random()*.42});}
 function frame(now){if(!document.hidden){if(now-swap>19000){scene=(scene+1)%scenes.length;swap=now;}
  var s=scenes[scene],g=ctx.createLinearGradient(0,0,w,h);g.addColorStop(0,s[0]);g.addColorStop(1,"#050509");ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
  var t=now*.00015;
  for(var k=0;k<3;k++){var x=w*(.18+k*.34)+Math.sin(t+k*2)*w*.08,y=h*(.25+(k%2)*.48)+Math.cos(t*1.3+k)*h*.06,r=Math.max(w,h)*(.22+k*.035),rg=ctx.createRadialGradient(x,y,0,x,y,r);rg.addColorStop(0,s[k+1]+"28");rg.addColorStop(1,s[k+1]+"00");ctx.fillStyle=rg;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();}
  for(var i=0;i<particles.length;i++){var p=particles[i];p.y-=p.v*.34;p.x+=Math.sin(t*3+p.p)*.18;if(p.y< -5){p.y=h+5;p.x=Math.random()*w;}ctx.globalAlpha=p.a*(.55+.45*Math.sin(t*8+p.p));ctx.fillStyle=i%3===0?s[2]:s[1];ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fill();}
  ctx.globalAlpha=1;
 }
 requestAnimationFrame(frame);
 }
 window.addEventListener("resize",resize,{passive:true});document.addEventListener("visibilitychange",function(){if(!document.hidden)requestAnimationFrame(frame)});
 resize();requestAnimationFrame(frame);
})();
