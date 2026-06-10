<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

const canvasRef = ref<HTMLCanvasElement | null>(null);
let animId = 0;
let t = 0;

function draw() {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const w = canvas.width;
  const h = canvas.height;
  ctx.fillStyle = "#0a0e1a";
  ctx.fillRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  for (let x = 0; x < w; x += 40) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Simulated camera feed
  ctx.fillStyle = "#111827";
  ctx.fillRect(20, 20, w - 40, h - 100);

  // Person detection box (animated)
  const bx = 120 + Math.sin(t * 0.02) * 30;
  const by = 80 + Math.cos(t * 0.015) * 15;
  ctx.strokeStyle = "#00d4a0";
  ctx.lineWidth = 2;
  ctx.strokeRect(bx, by, 80, 160);
  ctx.fillStyle = "rgba(0, 212, 160, 0.15)";
  ctx.fillRect(bx, by, 80, 160);
  ctx.fillStyle = "#00d4a0";
  ctx.font = "11px monospace";
  ctx.fillText("person 94.2%", bx, by - 6);

  // Telemetry gauges
  const altitude = 12 + Math.sin(t * 0.03) * 3;
  const distance = 4.2 + Math.cos(t * 0.025) * 1.5;
  const speed = 2.1 + Math.sin(t * 0.04) * 0.8;

  drawGauge(ctx, 30, h - 70, "ALT", altitude.toFixed(1) + "m", altitude / 20);
  drawGauge(ctx, 130, h - 70, "DIST", distance.toFixed(1) + "m", distance / 10);
  drawGauge(ctx, 230, h - 70, "SPD", speed.toFixed(1) + "m/s", speed / 5);

  // Mode label
  ctx.fillStyle = "#fbbf24";
  ctx.font = "bold 12px monospace";
  ctx.fillText("MODE: FOLLOW_PERSON (SITL)", w - 200, h - 20);

  t++;
  animId = requestAnimationFrame(draw);
}

function drawGauge(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  label: string,
  value: string,
  pct: number
) {
  ctx.fillStyle = "#64748b";
  ctx.font = "10px monospace";
  ctx.fillText(label, x, y);
  ctx.fillStyle = "#f1f5f9";
  ctx.font = "bold 14px monospace";
  ctx.fillText(value, x, y + 18);
  ctx.fillStyle = "rgba(255,255,255,0.1)";
  ctx.fillRect(x, y + 24, 80, 6);
  ctx.fillStyle = "#00bceb";
  ctx.fillRect(x, y + 24, 80 * Math.min(pct, 1), 6);
}

onMounted(() => {
  const canvas = canvasRef.value;
  if (canvas) {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = 280;
  }
  draw();
});

onUnmounted(() => cancelAnimationFrame(animId));
</script>

<template>
  <div class="demo-drone">
    <canvas ref="canvasRef" class="demo-drone-canvas" />
    <p class="demo-drone-caption">Simulated SITL telemetry — person detection + PID follow</p>
  </div>
</template>

<style scoped>
.demo-drone-canvas {
  width: 100%;
  height: 280px;
  border-radius: 8px;
  display: block;
}
.demo-drone-caption {
  font-size: 0.75rem;
  color: #64748b;
  margin: 0.5rem 0 0;
  text-align: center;
}
</style>
