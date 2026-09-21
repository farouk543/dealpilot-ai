# Same 4 documented architectural movements used for the exterior massing
# (services/design-agent/app/conversation.py), translated into their interior
# signature features. Kept to surface/material cues only (floor, walls,
# windows, mouldings) — a furniture item like a fireplace here would compete
# with the room's own furniture in the prompt and drag every room toward a
# generic living-room look regardless of room_type.
_STYLE_INTERIOR = {
    "haussmannien": (
        "Haussmannian Parisian architecture, herringbone parquet floor, "
        "ornate stucco cornice moulding, tall windows with wooden shutters, high ceilings"
    ),
    "moderniste": (
        "modernist architecture in the style of Le Corbusier, white plaster walls, "
        "ribbon windows with horizontal daylight, polished concrete floor, open floor plan"
    ),
    "contemporain": (
        "contemporary architecture, mix of light oak wood and pale concrete, "
        "large asymmetric glazed bay window, clean minimal lines, recessed lighting"
    ),
    "traditionnel": (
        "traditional French regional architecture, warm ochre plaster walls, "
        "exposed wooden beams, terracotta tile floor, wooden shutters"
    ),
}

# Same 4 styles, but landscaping/facade cues instead of interior surfaces —
# a parquet floor or ceiling moulding means nothing outdoors, so the garden
# render needs its own vocabulary rather than reusing _STYLE_INTERIOR.
_STYLE_EXTERIOR = {
    "haussmannien": (
        "Parisian courtyard garden, wrought-iron fence, gravel pathway, "
        "clipped boxwood hedges, classic cut-stone facade in the background"
    ),
    "moderniste": (
        "minimalist modernist garden in the style of Le Corbusier, geometric concrete pavers, "
        "architectural planting, crisp lawn edges, white facade with ribbon windows in the background"
    ),
    "contemporain": (
        "contemporary garden design, wooden deck, mixed textures, ornamental grasses, "
        "large glazed facade in the background"
    ),
    "traditionnel": (
        "French country garden, lavender borders, gravel paths, low stone wall, climbing roses, "
        "ochre facade with wooden shutters in the background"
    ),
}

# (display label, furniture/fixtures) — the label is repeated in the prompt to
# keep the room type from being diluted by the longer style description.
# Residential rooms (salon, chambre...) and commercial spaces (vitrine, bureau...)
# are deliberately kept in one dict, but the frontend only ever offers the
# subset that matches the building's actual type (see INTERIOR_ROOM_TYPES /
# _building_category in frontend/app.py) — a commercial building is never
# offered a "chambre" (bedroom) button, and vice versa.
_ROOM_VOCAB = {
    "salon": ("living room", "sofa, coffee table, marble fireplace, natural daylight"),
    "chambre": ("bedroom", "bed with linen bedding, bedside tables, soft lighting"),
    "cuisine": ("kitchen", "countertop, cabinetry, cooking island, pendant lights"),
    "salle de bain": ("bathroom", "walk-in shower, vanity, tiled walls, bathtub"),
    "jardin": ("garden", "lawn, flower beds, hedge-lined pathway, garden furniture"),
    "vitrine": ("shopfront window display", "large glazed storefront, product display stands, illuminated signage"),
    "espace de vente": ("retail sales floor", "shelving units, product displays, checkout counter, bright ambient lighting"),
    "bureau": ("office", "desk, ergonomic chair, bookshelf, computer monitor, natural daylight"),
    "sanitaires": ("public restroom", "sink counter, mirror, hand dryer, tiled walls, stall doors"),
}

_OUTDOOR_ROOMS = {"jardin"}

_FACADE_ROOM = "facade"

# Facade-only material/opening cues, distinct from _STYLE_EXTERIOR's landscaping
# vocabulary — a garden render puts the building in the background, this one
# makes the building itself the subject.
_STYLE_FACADE = {
    "haussmannien": (
        "Haussmannian Parisian facade, cut cream limestone, wrought-iron Juliet balconies, "
        "tall French windows with dark wooden shutters, zinc roofing details"
    ),
    "moderniste": (
        "modernist facade in the style of Le Corbusier, white plaster walls, ribbon windows, "
        "exposed structural pilotis, flat clean surfaces"
    ),
    "contemporain": (
        "contemporary facade, mix of light oak wood cladding and pale concrete panels, "
        "large asymmetric glazed openings, clean minimal lines"
    ),
    "traditionnel": (
        "traditional French regional facade, warm ochre plaster walls, exposed wooden beams, "
        "stone window surrounds, wooden shutters"
    ),
}

_ROOF_DESC = {
    "plat": "flat roof",
    "deux pans": "pitched roof with two slopes",
    "quatre pans": "hipped roof with four slopes",
}

# 8 standard architectural-photography angles, 45deg apart, for the 360
# facade view — SDXL has no notion of a shared 3D scene between calls, so
# "turning around the building" only exists as far as these text descriptions
# (plus a shared seed, see generator.py) make each generation consistent with
# the others. Elevated (not eye-level) on purpose: a straight-on eye-level
# shot let SDXL crop in tight on 1-2 floors of windows, cutting off the roof
# and most of the building — a slightly elevated drone-style angle keeps the
# entire building, foundation to roofline, inside the frame.
_ANGLE_VIEW_DESC = {
    0: "distant elevated drone view of the front facade",
    45: "distant elevated drone view from the front-right corner",
    90: "distant elevated drone view of the right side facade",
    135: "distant elevated drone view from the rear-right corner",
    180: "distant elevated drone view of the rear facade",
    225: "distant elevated drone view from the rear-left corner",
    270: "distant elevated drone view of the left side facade",
    315: "distant elevated drone view from the front-left corner",
}

# Fed as this generation's negative_prompt (see generator.py) — the shared
# generic negative prompt used for rooms/garden doesn't exclude close-ups,
# but a 360 facade tour specifically needs the WHOLE building in frame, so
# tight/cropped compositions have to be actively pushed away rather than
# just not requested.
FACADE_NEGATIVE_PROMPT = (
    "close-up, closeup, cropped, zoomed in, macro, partial building, cut off roof, "
    "cut off building, out of frame, detail shot, blurry, low quality, distorted, "
    "deformed, watermark, text, logo, people, person, cartoon, illustration"
)

_DEFAULT_STYLE = "contemporain"
_DEFAULT_ROOM = "salon"


def _article(label: str) -> str:
    return "an" if label[:1].lower() in "aeiou" else "a"


def build_facade_prompt(
    architectural_style: str,
    building_type: str,
    floors: int | None,
    roof_type: str | None,
    notes: str | None,
    angle_deg: int = 0,
) -> str:
    style_desc = _STYLE_FACADE.get(architectural_style.lower(), _STYLE_FACADE[_DEFAULT_STYLE])
    floors_desc = f"a {floors}-story" if floors else "a multi-story"
    roof_desc = _ROOF_DESC.get((roof_type or "").lower(), "flat roof")
    view_desc = _ANGLE_VIEW_DESC.get(angle_deg, _ANGLE_VIEW_DESC[0])
    # CLIP (SDXL's text encoder) hard-truncates at 77 tokens — the framing
    # instructions used to be appended at the end and were silently dropped
    # once the rest of the prompt (style description, boilerplate) pushed the
    # total past that limit (measured: 118 tokens, everything past ~77 cut).
    # The fix isn't "make the prompt shorter" so much as "put what MUST
    # survive truncation first": framing/distance leads, generic photography
    # boilerplate trails last since losing that costs the least.
    prompt = (
        f"aerial drone photo, entire {floors_desc} {building_type} building small and fully visible "
        f"from far away, tiny in frame, wide empty sky and ground on all sides, not zoomed in, "
        f"{view_desc}, {roof_desc}, {style_desc}. "
        "Photorealistic, architectural photography, high detail, professional real-estate exterior photo."
    )
    if notes:
        prompt += f" Additional preferences: {notes}."
    return prompt


def build_prompt(
    room_type: str,
    architectural_style: str,
    building_type: str,
    notes: str | None,
    floors: int | None = None,
    roof_type: str | None = None,
) -> str:
    room_key = room_type.lower()

    if room_key == _FACADE_ROOM:
        return build_facade_prompt(architectural_style, building_type, floors, roof_type, notes)

    is_outdoor = room_key in _OUTDOOR_ROOMS
    room_label, room_furniture = _ROOM_VOCAB.get(room_key, _ROOM_VOCAB[_DEFAULT_ROOM])

    if is_outdoor:
        style_desc = _STYLE_EXTERIOR.get(architectural_style.lower(), _STYLE_EXTERIOR[_DEFAULT_STYLE])
        prompt = (
            f"{room_label} landscape photograph, {_article(room_label)} {room_label} with {room_furniture}, "
            f"{style_desc}, for a {building_type} building. "
            "Photorealistic, architectural photography, wide angle lens, natural daylight, "
            "high detail, professional real-estate exterior photo, no people, no text, no watermark."
        )
    else:
        style_desc = _STYLE_INTERIOR.get(architectural_style.lower(), _STYLE_INTERIOR[_DEFAULT_STYLE])
        prompt = (
            f"{room_label} interior photograph, {_article(room_label)} {room_label} with {room_furniture}, "
            f"{style_desc}, in a {building_type} building. "
            "Photorealistic, architectural photography, wide angle lens, soft natural light, "
            "high detail, professional real-estate interior photo, no people, no text, no watermark."
        )
    if notes:
        prompt += f" Additional preferences: {notes}."
    return prompt
