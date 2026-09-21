from pydantic import BaseModel


class InteriorRenderRequest(BaseModel):
    room_type: str
    architectural_style: str
    building_type: str = "residentiel"
    notes: str | None = None
    # Only used when room_type == "facade", to describe the actual building
    # being designed rather than a generic exterior shot.
    floors: int | None = None
    roof_type: str | None = None
    # When the frontend has already generated the 360 facade view for this
    # building, it passes that batch's shared seed here so room renders come
    # out visually consistent with it (same style/color "family") instead of
    # each being an independent, unrelated random draw.
    seed: int | None = None


class InteriorRenderResult(BaseModel):
    image_url: str | None = None
    prompt_used: str
    provider: str = "replicate"
    model: str
    error: str | None = None


class Facade360Request(BaseModel):
    architectural_style: str
    building_type: str = "residentiel"
    floors: int | None = None
    roof_type: str | None = None
    notes: str | None = None
    angle_count: int = 8


class Facade360Image(BaseModel):
    angle_deg: int
    image_url: str


class Facade360Result(BaseModel):
    images: list[Facade360Image] = []
    seed: int | None = None
    model: str
    error: str | None = None
