"""360-degree facade viewer: a fixed set of SDXL-generated angle shots
(services/interior-render's generate_facade_360) swapped by drag position,
the same interaction as an e-commerce product-photo 360 spinner. Not a real
3D model — each image is an independent 2D photo, sharing only a random seed
for visual consistency across angles (see generator.py's docstring)."""

from string import Template

_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; font-family: sans-serif; background: #eef2f5; }
  #stage {
    position: relative; width: 100%; height: 520px; background: #111;
    overflow: hidden; cursor: grab; touch-action: none; user-select: none;
  }
  #stage.dragging { cursor: grabbing; }
  #stage img {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    object-fit: cover; display: none; pointer-events: none;
  }
  #stage img.active { display: block; }
  #hint {
    padding: 8px 14px; font-size: 12px; color: #666;
    background: rgba(255,255,255,0.9);
  }
</style>
</head>
<body>
<div id="stage">
$img_tags
</div>
<div id="hint">Glisser horizontalement pour faire tourner le batiment ($count angles)</div>
<script>
  const stage = document.getElementById('stage');
  const imgs = Array.from(stage.querySelectorAll('img'));
  let current = 0;

  function show(i) {
    current = ((i % imgs.length) + imgs.length) % imgs.length;
    imgs.forEach((img, idx) => img.classList.toggle('active', idx === current));
  }
  show(0);

  let dragging = false;
  let startX = 0;
  let startIndex = 0;
  const stepPx = 40;

  stage.addEventListener('pointerdown', (e) => {
    dragging = true;
    startX = e.clientX;
    startIndex = current;
    stage.classList.add('dragging');
    stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const delta = e.clientX - startX;
    show(startIndex + Math.round(-delta / stepPx));
  });
  stage.addEventListener('pointerup', () => {
    dragging = false;
    stage.classList.remove('dragging');
  });
  stage.addEventListener('pointerleave', () => {
    dragging = false;
    stage.classList.remove('dragging');
  });
</script>
</body>
</html>
"""
)


def render_facade_360_html(images: list[dict]) -> str:
    """images: list of {"angle_deg": int, "image_url": str}."""
    ordered = sorted(images, key=lambda im: im["angle_deg"])
    img_tags = "\n".join(
        f'  <img src="{im["image_url"]}" class="{"active" if i == 0 else ""}" alt="Facade a {im["angle_deg"]} degres">'
        for i, im in enumerate(ordered)
    )
    return _TEMPLATE.substitute(img_tags=img_tags, count=len(ordered))
