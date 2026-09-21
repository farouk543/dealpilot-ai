import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    intake_url: str = field(default_factory=lambda: os.environ.get("INTAKE_SERVICE_URL", "http://intake:8000"))
    document_intel_url: str = field(
        default_factory=lambda: os.environ.get("DOCUMENT_INTEL_SERVICE_URL", "http://document-intel:8000")
    )
    vision_url: str = field(default_factory=lambda: os.environ.get("VISION_SERVICE_URL", "http://vision:8000"))
    market_url: str = field(default_factory=lambda: os.environ.get("MARKET_SERVICE_URL", "http://market:8000"))
    location_intel_url: str = field(
        default_factory=lambda: os.environ.get("LOCATION_INTEL_SERVICE_URL", "http://location-intel:8000")
    )
    financial_engine_url: str = field(
        default_factory=lambda: os.environ.get("FINANCIAL_ENGINE_SERVICE_URL", "http://financial-engine:8000")
    )
    risk_url: str = field(default_factory=lambda: os.environ.get("RISK_SERVICE_URL", "http://risk:8000"))
    offer_url: str = field(default_factory=lambda: os.environ.get("OFFER_SERVICE_URL", "http://offer:8000"))
    due_diligence_url: str = field(
        default_factory=lambda: os.environ.get("DUE_DILIGENCE_SERVICE_URL", "http://due-diligence:8000")
    )
    land_feasibility_url: str = field(
        default_factory=lambda: os.environ.get("LAND_FEASIBILITY_SERVICE_URL", "http://land-feasibility:8000")
    )
    design_agent_url: str = field(
        default_factory=lambda: os.environ.get("DESIGN_AGENT_SERVICE_URL", "http://design-agent:8000")
    )
    interior_render_url: str = field(
        default_factory=lambda: os.environ.get("INTERIOR_RENDER_SERVICE_URL", "http://interior-render:8000")
    )
    exterior_render_url: str = field(
        default_factory=lambda: os.environ.get("EXTERIOR_RENDER_SERVICE_URL", "http://exterior-render:8000")
    )
    summary_url: str = field(default_factory=lambda: os.environ.get("SUMMARY_SERVICE_URL", "http://summary:8000"))
    report_url: str = field(default_factory=lambda: os.environ.get("REPORT_SERVICE_URL", "http://report:8000"))


settings = Settings()
