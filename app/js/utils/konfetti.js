// ============================================================
// KONFETTI — canvas confetti animation
// ============================================================

function fireConfetti(opts){
  opts = opts || {};
  const canvas = document.getElementById("confettiCanvas");
  if(!canvas) return;

  const ctx = canvas.getContext("2d");
  canvas.classList.add("active");

  let W = canvas.width  = window.innerWidth;
  let H = canvas.height = window.innerHeight;

  const colors = opts.colors || [
    "#f97316", "#10b981", "#0a1e3f", "#fbbf24",
    "#3b82f6", "#ef4444", "#8b5cf6", "#ec4899"
  ];
  const count    = opts.count    || 180;
  const duration = opts.duration || 5500;

  const particles = [];
  for(let i = 0; i < count; i++){
    particles.push({
      x:        Math.random() * W,
      y:        -20 - Math.random() * H * 0.6,
      vx:       (Math.random() - 0.5) * 5,
      vy:       2 + Math.random() * 5,
      size:     5 + Math.random() * 9,
      color:    colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * Math.PI * 2,
      rotSpeed: (Math.random() - 0.5) * 0.25,
      shape:    Math.random() < 0.55 ? "rect" : "circle",
      drift:    (Math.random() - 0.5) * 0.6
    });
  }

  const start = performance.now();
  let rafId = null;

  function frame(now){
    const elapsed = now - start;
    ctx.clearRect(0, 0, W, H);

    particles.forEach(p => {
      p.x += p.vx + Math.sin((elapsed + p.rotation * 100) / 400) * p.drift;
      p.y += p.vy;
      p.vy += 0.06;
      p.rotation += p.rotSpeed;

      // Loop: επαναφορά στην κορυφή
      if(p.y > H + 40){
        p.y  = -20;
        p.x  = Math.random() * W;
        p.vy = 2 + Math.random() * 4;
      }

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.min(1, (duration - elapsed) / 1000 + 0.3);

      if(p.shape === "circle"){
        ctx.beginPath();
        ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
      }
      ctx.restore();
    });

    if(elapsed < duration){
      rafId = requestAnimationFrame(frame);
    } else {
      canvas.classList.remove("active");
      ctx.clearRect(0, 0, W, H);
    }
  }

  function onResize(){
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  window.addEventListener("resize", onResize);

  // Cleanup safety
  setTimeout(() => {
    if(rafId) cancelAnimationFrame(rafId);
    window.removeEventListener("resize", onResize);
    canvas.classList.remove("active");
    ctx.clearRect(0, 0, W, H);
  }, duration + 500);

  rafId = requestAnimationFrame(frame);
}