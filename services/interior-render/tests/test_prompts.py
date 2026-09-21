from app.prompts import FACADE_NEGATIVE_PROMPT, build_facade_prompt, build_prompt


def test_known_style_and_room_are_reflected():
    prompt = build_prompt("cuisine", "moderniste", "residentiel", None)
    assert "kitchen" in prompt
    assert "Le Corbusier" in prompt


def test_unknown_style_falls_back_to_default():
    prompt = build_prompt("salon", "futuriste-inexistant", "residentiel", None)
    assert "contemporary architecture" in prompt


def test_notes_are_appended():
    prompt = build_prompt("chambre", "traditionnel", "residentiel", "murs bleu clair")
    assert "murs bleu clair" in prompt


def test_garden_uses_exterior_vocabulary_not_interior():
    prompt = build_prompt("jardin", "haussmannien", "collectif residentiel", None)
    assert "garden" in prompt
    assert "landscape photograph" in prompt
    assert "boxwood hedges" in prompt
    assert "parquet" not in prompt


def test_garden_falls_back_to_default_exterior_style():
    prompt = build_prompt("jardin", "futuriste-inexistant", "residentiel", None)
    assert "contemporary garden design" in prompt


def test_facade_reflects_floors_and_roof():
    prompt = build_prompt("facade", "haussmannien", "residentiel", None, floors=3, roof_type="deux pans")
    assert "3-story" in prompt
    assert "pitched roof with two slopes" in prompt
    assert "Haussmannian Parisian facade" in prompt
    assert "front facade" in prompt
    assert "entire" in prompt.lower() and "visible" in prompt.lower()


def test_facade_falls_back_when_floors_and_roof_missing():
    prompt = build_prompt("facade", "contemporain", "residentiel", None)
    assert "multi-story" in prompt
    assert "flat roof" in prompt


def test_facade_uses_facade_vocabulary_not_garden():
    prompt = build_prompt("facade", "haussmannien", "residentiel", None, floors=2, roof_type="plat")
    assert "boxwood hedges" not in prompt
    assert "landscape photograph" not in prompt


def test_commercial_rooms_use_commercial_vocabulary():
    prompt = build_prompt("vitrine", "contemporain", "local commercial", None)
    assert "shopfront" in prompt
    assert "bed" not in prompt

    prompt = build_prompt("bureau", "contemporain", "local commercial", None)
    assert "office" in prompt
    assert "desk" in prompt


def test_facade_360_angles_produce_distinct_view_descriptions():
    front = build_facade_prompt("contemporain", "residentiel", 2, "plat", None, angle_deg=0)
    rear = build_facade_prompt("contemporain", "residentiel", 2, "plat", None, angle_deg=180)
    side = build_facade_prompt("contemporain", "residentiel", 2, "plat", None, angle_deg=90)
    assert "front facade" in front
    assert "rear facade" in rear
    assert "right side facade" in side
    assert front != rear != side


def test_facade_360_views_are_elevated_not_eye_level():
    # An eye-level shot let SDXL crop tight on a couple of floors of windows
    # and cut off the roof — every angle must ask for an elevated framing
    # instead, so the whole building stays in frame.
    for angle in (0, 45, 90, 135, 180, 225, 270, 315):
        prompt = build_facade_prompt("contemporain", "residentiel", 2, "plat", None, angle_deg=angle)
        assert "elevated" in prompt
        assert "eye-level" not in prompt
        assert "entire" in prompt.lower() and "visible" in prompt.lower()


def test_facade_negative_prompt_excludes_tight_crops():
    assert "cropped" in FACADE_NEGATIVE_PROMPT
    assert "close-up" in FACADE_NEGATIVE_PROMPT
    assert "cut off building" in FACADE_NEGATIVE_PROMPT


def test_facade_360_unknown_angle_falls_back_to_front():
    prompt = build_facade_prompt("contemporain", "residentiel", 2, "plat", None, angle_deg=999)
    assert "front facade" in prompt


def test_article_agrees_with_vowel_initial_room_label():
    prompt = build_prompt("bureau", "contemporain", "local commercial", None)
    assert "an office" in prompt
    assert "a office" not in prompt

    prompt = build_prompt("cuisine", "contemporain", "residentiel", None)
    assert "a kitchen" in prompt
