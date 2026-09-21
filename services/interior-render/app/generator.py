import os
import threading
import uuid

import torch
from diffusers import AutoencoderKL, DPMSolverMultistepScheduler, StableDiffusionXLPipeline

from dealpilot_shared import Facade360Image, Facade360Request, Facade360Result, InteriorRenderRequest, InteriorRenderResult
from dealpilot_shared.gpu_lock import gpu_lock
from dealpilot_shared.logging_utils import get_logger

from .prompts import FACADE_NEGATIVE_PROMPT, build_facade_prompt, build_prompt

_DEFAULT_NEGATIVE_PROMPT = (
    "blurry, low quality, distorted, deformed, watermark, text, logo, people, person, cartoon, illustration"
)

_FACADE_360_ANGLES = (0, 45, 90, 135, 180, 225, 270, 315)

_MODEL_ID = os.environ.get("SD_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
_PUBLIC_URL = os.environ.get("INTERIOR_RENDER_PUBLIC_URL", "http://localhost:8022")
RENDERS_DIR = os.environ.get("RENDERS_DIR", "/data/renders")

_logger = get_logger(__name__)

_pipe = None
_load_error: str | None = None

# There is exactly one GPU. Two requests calling the pipeline concurrently
# would either crash (CUDA out-of-memory / concurrent kernel corruption) or
# silently interleave denoising steps between two unrelated images. This lock
# serializes generation: a second request simply waits its turn instead of
# racing the first one on the GPU.
_gpu_lock = threading.Lock()


def is_model_loaded() -> bool:
    return _pipe is not None


def _get_pipeline():
    """Loads the model once, lazily, on first request, and keeps it resident on the GPU."""
    global _pipe, _load_error
    if _pipe is not None or _load_error is not None:
        return _pipe
    try:
        # The stock SDXL VAE produces NaNs in float16, so diffusers silently upcasts it to
        # float32 at decode time. On an 8GB GPU already near-full from the fp16 UNet, that
        # upcast overflows dedicated VRAM and the driver falls back to a very slow memory
        # swap instead of crashing (observed: ~295s total for a generation whose 30-step
        # diffusion loop alone takes ~25s). This community VAE was retrained to work
        # correctly in float16, so it never triggers that upcast.
        vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
        pipe = StableDiffusionXLPipeline.from_pretrained(
            _MODEL_ID,
            vae=vae,
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        )
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        _pipe = pipe.to("cuda")
    except Exception as exc:
        _load_error = str(exc)
    return _pipe


def generate_interior(request: InteriorRenderRequest) -> InteriorRenderResult:
    prompt = build_prompt(
        request.room_type,
        request.architectural_style,
        request.building_type,
        request.notes,
        request.floors,
        request.roof_type,
    )
    model_label = f"Stable Diffusion XL (auto-heberge, {_MODEL_ID})"
    # Reusing the 360-facade batch's seed (when the frontend already generated
    # one for this building) keeps this room visually "in the same family" as
    # the facade instead of being an unrelated independent draw.
    generator = torch.Generator(device="cuda").manual_seed(request.seed) if request.seed is not None else None

    if _gpu_lock.locked():
        _logger.info("GPU busy, request for %s queued behind the current generation", request.room_type)
    with _gpu_lock:
        # In-process lock above serializes concurrent requests to this
        # service; this one also serializes against exterior-render's Cycles
        # renders, which share the same physical GPU from a separate
        # container the threading.Lock above can't see.
        with gpu_lock():
            return _generate_locked(prompt, model_label, generator=generator)


def _generate_locked(
    prompt: str, model_label: str, generator: torch.Generator | None = None, negative_prompt: str = _DEFAULT_NEGATIVE_PROMPT
) -> InteriorRenderResult:
    pipe = _get_pipeline()
    if pipe is None:
        return InteriorRenderResult(
            prompt_used=prompt,
            model=model_label,
            provider="self-hosted",
            error=_load_error or "Le modele n'a pas pu etre charge sur le GPU.",
        )

    try:
        image = pipe(
            prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=30,
            guidance_scale=7.0,
            height=1024,
            width=1024,
            generator=generator,
        ).images[0]

        os.makedirs(RENDERS_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        image.save(os.path.join(RENDERS_DIR, filename))

        return InteriorRenderResult(
            image_url=f"{_PUBLIC_URL}/images/{filename}",
            prompt_used=prompt,
            model=model_label,
            provider="self-hosted",
        )
    except Exception as exc:
        return InteriorRenderResult(prompt_used=prompt, model=model_label, provider="self-hosted", error=str(exc))


def generate_facade_360(request: Facade360Request) -> Facade360Result:
    """Generates a fixed set of angle shots around the building (front, side,
    rear, etc.) sharing ONE random seed across all of them. SDXL has no
    concept of a persistent 3D scene between independent calls, so a shared
    seed — keeping everything else (prompt structure, style, dimensions)
    identical and varying only the angle description — is the best available
    lever for visual consistency without a heavier multi-view model."""
    model_label = f"Stable Diffusion XL (auto-heberge, {_MODEL_ID})"
    angles = _FACADE_360_ANGLES if request.angle_count > 4 else (0, 90, 180, 270)

    if _gpu_lock.locked():
        _logger.info("GPU busy, 360 facade batch (%d angles) queued behind the current generation", len(angles))
    with _gpu_lock:
        with gpu_lock():
            pipe = _get_pipeline()
            if pipe is None:
                return Facade360Result(model=model_label, error=_load_error or "Le modele n'a pas pu etre charge sur le GPU.")

            seed = torch.seed() % (2**32)
            images: list[Facade360Image] = []
            for angle in angles:
                prompt = build_facade_prompt(
                    request.architectural_style, request.building_type, request.floors, request.roof_type, request.notes, angle
                )
                generator = torch.Generator(device="cuda").manual_seed(seed)
                result = _generate_locked(prompt, model_label, generator=generator, negative_prompt=FACADE_NEGATIVE_PROMPT)
                if result.error:
                    return Facade360Result(images=images, model=model_label, error=result.error)
                images.append(Facade360Image(angle_deg=angle, image_url=result.image_url))

            return Facade360Result(images=images, seed=seed, model=model_label)
