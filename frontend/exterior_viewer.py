"""Interactive viewer for the Blender/Cycles-generated massing model
(services/exterior-render), replacing the old hand-rolled Three.js scene
(massing_3d.py, retired). <model-viewer> (Google, open source) gives much
better default PBR/IBL rendering than the custom Three.js scene did, at the
cost of the construction-phase timeline now driving a real glTF animation's
currentTime instead of a custom clip-plane shader trick.
"""

import json
from string import Template

_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html>
<head>
<script type="module" src="https://cdnjs.cloudflare.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>
<style>
  body { margin: 0; background: #eef2f5; font-family: sans-serif; }
  model-viewer {
    width: 100%; height: 620px; background: #dce6ee;
    --progress-bar-color: transparent;
  }
  #hint {
    position: absolute; margin: 8px; font-size: 11px; color: #666;
    background: rgba(255,255,255,0.85); padding: 4px 8px; border-radius: 6px;
  }
  #timeline {
    font-family: sans-serif; background: rgba(255,255,255,0.95);
    padding: 10px 14px; border-top: 1px solid #ddd;
  }
  #timeline .row { display: flex; align-items: center; gap: 10px; }
  #playBtn {
    border: none; background: #3a6ea5; color: white; padding: 6px 12px;
    border-radius: 6px; cursor: pointer; font-size: 13px; flex-shrink: 0;
  }
  #playBtn:hover { background: #2f5c8a; }
  #phaseSlider { flex: 1; }
  #phaseLabel { font-size: 12px; color: #333; margin-top: 4px; }
</style>
</head>
<body>
<div style="position:relative;">
  <model-viewer id="mv" src="$model_url" camera-controls shadow-intensity="1" exposure="1.1"
    environment-image="neutral" alt="Volume 3D indicatif"></model-viewer>
  <div id="hint">Glisser pour tourner &middot; molette pour zoomer</div>
</div>
<div id="timeline">
  <div class="row">
    <button id="playBtn">&#9654; Simuler la construction</button>
    <input type="range" id="phaseSlider" min="0" max="$max_index" value="$max_index" step="1">
  </div>
  <div id="phaseLabel">Batiment termine</div>
</div>
<script>
  const phaseLabels = $phase_labels_json;
  const fps = $fps;
  const endFrame = $end_frame;
  const framesPerPhase = endFrame / phaseLabels.length;
  const mv = document.getElementById('mv');
  const slider = document.getElementById('phaseSlider');
  const phaseLabelEl = document.getElementById('phaseLabel');
  const playBtn = document.getElementById('playBtn');

  function applyPhase(idx) {
    idx = Math.max(0, Math.min(phaseLabels.length - 1, idx));
    mv.pause();
    const isLast = idx === phaseLabels.length - 1;
    mv.currentTime = isLast ? (endFrame / fps) : ((framesPerPhase * idx) / fps);
    phaseLabelEl.textContent = 'Etape ' + (idx + 1) + '/' + phaseLabels.length + ' — ' + phaseLabels[idx];
  }

  slider.addEventListener('input', () => applyPhase(parseInt(slider.value, 10)));

  let playing = false;
  let playTimer = null;
  playBtn.addEventListener('click', () => {
    if (playing) {
      clearInterval(playTimer);
      playing = false;
      playBtn.textContent = '▶ Simuler la construction';
      return;
    }
    playing = true;
    playBtn.textContent = '⏸ Pause';
    slider.value = 0;
    applyPhase(0);
    playTimer = setInterval(() => {
      const next = parseInt(slider.value, 10) + 1;
      slider.value = next;
      applyPhase(next);
      if (next >= phaseLabels.length - 1) {
        clearInterval(playTimer);
        playing = false;
        playBtn.textContent = '▶ Simuler la construction';
      }
    }, 700);
  });

  mv.addEventListener('load', () => applyPhase(phaseLabels.length - 1));
</script>
</body>
</html>
"""
)


def render_exterior_viewer_html(model_url: str, phase_labels: list[str], fps: float, end_frame: int) -> str:
    return _TEMPLATE.substitute(
        model_url=model_url,
        phase_labels_json=json.dumps(phase_labels),
        fps=fps,
        end_frame=end_frame,
        max_index=max(0, len(phase_labels) - 1),
    )
