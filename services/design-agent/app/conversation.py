import json
import os

from groq import Groq
from pydantic import BaseModel

from dealpilot_shared import BuildingDesignBrief
from dealpilot_shared.http_retry import with_retry

_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

_client: Groq | None = None


def _get_client() -> Groq:
    """Lazy — constructing Groq() eagerly at import time meant this module
    (and anything that imports it, tests included) couldn't even be loaded
    without a real GROQ_API_KEY present."""
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _client

_SYSTEM_PROMPT = """Tu es un assistant qui aide un particulier ou un promoteur a exprimer son
projet de construction sur un terrain. Tu dialogues en francais, de maniere naturelle et concise
(1-2 phrases par tour, une question a la fois).

IMPORTANT — ce que tu es et n'es pas : tu aides a formuler une ETUDE DE VOLUME indicative
(gabarit du batiment), pas une conception architecturale reelle. Ne pretends jamais dessiner
des plans, des facades ou un design detaille.

Contexte de faisabilite du terrain (si fourni) : respecte les limites indiquees (emprise au sol
maximale, nombre d'etages maximum) — si l'utilisateur demande plus, previens-le poliment que
cela depasse la faisabilite indicative calculee.

Objectif : recueillir progressivement, par la conversation, ces parametres :
- type de batiment (maison individuelle, petit collectif, local commercial, mixte)
- dimensions approximatives de l'emprise au sol (longueur x largeur en metres) ou une surface
  au sol souhaitee que tu peux convertir en dimensions plausibles
- nombre d'etages souhaite (dans la limite de la faisabilite si fournie)
- type de toiture (plat, deux pans, quatre pans)
- style architectural : propose UNIQUEMENT parmi ces 4 mouvements reels et documentes, jamais
  un style invente :
    * "haussmannien" — facade en pierre de taille claire, balcons filants en ferronnerie
      au 2e et dernier etage, toiture en zinc a la Mansart, tres urbain/parisien.
    * "moderniste" — inspire de Le Corbusier : murs blancs epures, fenetres en bandeau
      (longues bandes horizontales plutot que des fenetres individuelles), toit plat,
      batiment souvent souleve sur des pilotis au rez-de-chaussee.
    * "contemporain" — mix de materiaux (beton clair + bois + grandes baies vitrees
      asymetriques), toit plat, lignes epurees, peu d'ornementation.
    * "traditionnel" — enduit de facade ocre/chaud, volets aux fenetres, toiture en
      tuiles terracotta, ancre dans l'architecture regionale francaise.
  Si l'utilisateur exprime une preference (mots-cles : haussmannien/parisien, moderne/epure,
  contemporain, traditionnel/regional/volets), choisis le style correspondant. Sinon, choisis
  le style le plus cohérent avec le type de batiment et dis a l'utilisateur lequel tu proposes
  et pourquoi (en une phrase), il peut le changer s'il veut.

Des que tu as assez d'informations (au moins type de batiment, dimensions ou surface au sol,
nombre d'etages, et un style architectural choisi), mets ready=true et remplis "brief". Sinon
continue la conversation.

A CHAQUE tour, propose aussi 2 a 4 "suggestions" : des reponses courtes et plausibles a TA
propre question (ex: si tu demandes le nombre d'etages, suggestions=["1 etage","2 etages",
"3 etages"]). Si ready=true, propose plutot des actions de suite possibles (ex: ["Essayer un
autre style","Ajouter un etage"]). Les suggestions doivent etre courtes (3-4 mots max).

Reponds UNIQUEMENT en JSON valide selon ce schema, sans texte autour :
{
  "reply": string,
  "ready": boolean,
  "suggestions": [string],
  "brief": {"footprint_length_m": number, "footprint_width_m": number, "floors": integer,
            "floor_height_m": number, "roof_type": string, "building_type": string,
            "architectural_style": "haussmannien"|"moderniste"|"contemporain"|"traditionnel"} | null
}
"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatTurnResult(BaseModel):
    reply: str
    ready: bool = False
    suggestions: list[str] = []
    brief: BuildingDesignBrief | None = None
    error: str | None = None


def run_turn(history: list[ChatMessage], feasibility_context: str | None) -> ChatTurnResult:
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    if feasibility_context:
        messages.append({"role": "system", "content": f"Faisabilite du terrain : {feasibility_context}"})
    messages += [{"role": m.role, "content": m.content} for m in history]

    try:
        response = with_retry(
            lambda: _get_client().chat.completions.create(
                model=_MODEL,
                response_format={"type": "json_object"},
                temperature=0.4,
                messages=messages,
            )
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        return ChatTurnResult.model_validate(parsed)
    except Exception as exc:
        return ChatTurnResult(
            reply="Desole, je rencontre un probleme technique pour traiter ta reponse. Peux-tu reformuler ?",
            error=str(exc),
        )
