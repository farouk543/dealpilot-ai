"""Runs every synthetic case in data/synthetic_cases/ against the live orchestrator,
checks each case's expected_checks against the real response, and writes:
  - eval/results/<case_id>.json  (raw response, for audit)
  - docs/eval_results.md         (human-readable report)

Usage: run the full stack (docker compose up -d), then:
    py eval/run_eval.py
"""

import json
import subprocess
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "data" / "synthetic_cases"
RESULTS_DIR = ROOT / "eval" / "results"
ORCHESTRATOR_URL = "http://localhost:8010"


def _docker(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=False, capture_output=True)


def _submit_case(case: dict) -> tuple[int | None, dict | str]:
    form = {k: str(v) for k, v in case["form"].items()}
    files = []
    for doc_name in case.get("documents", []):
        path = CASES_DIR / doc_name
        files.append(("documents", (doc_name, path.read_bytes(), "text/plain")))
    for photo_name in case.get("photos", []):
        path = CASES_DIR / photo_name
        files.append(("photos", (photo_name, path.read_bytes(), "image/jpeg")))

    try:
        response = requests.post(f"{ORCHESTRATOR_URL}/deals", data=form, files=files, timeout=180)
    except requests.RequestException as exc:
        return None, f"EXCEPTION lors de la requete : {exc}"

    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


def _run_check(check: dict, status: int | None, result) -> tuple[str, str]:
    """Returns (verdict, detail). verdict is one of: PASS, FAIL, INFO."""
    ctype = check["type"]

    if ctype == "known_gap":
        return "INFO", check["note"]

    if not isinstance(result, dict):
        return "FAIL", f"reponse non-JSON ou erreur de transport : {result}"

    if ctype == "http_status":
        ok = status == check["value"]
        return ("PASS" if ok else "FAIL"), f"status={status} (attendu {check['value']})"

    if ctype == "no_crash":
        ok = status is not None and status < 500
        return ("PASS" if ok else "FAIL"), f"status={status}"

    prop = result.get("property") or {}

    if ctype == "field_contested":
        field = prop.get(check["field"], {})
        ok = bool(field.get("contested"))
        return ("PASS" if ok else "FAIL"), f"contested={field.get('contested')}, candidates={field.get('candidates')}"

    if ctype == "field_not_contested":
        field = prop.get(check["field"], {})
        ok = not field.get("contested")
        return ("PASS" if ok else "FAIL"), f"contested={field.get('contested')}"

    if ctype == "field_value_not_equal":
        field = prop.get(check["field"], {})
        values = [c["value"] for c in field.get("candidates", [])]
        ok = check["forbidden_value"] not in values
        return ("PASS" if ok else "FAIL"), f"candidates observes={values}"

    if ctype == "underwriting_present":
        ok = result.get("underwriting") is not None
        return ("PASS" if ok else "FAIL"), f"underwriting present={ok}"

    risks = (result.get("risk_register") or {}).get("risks", [])

    if ctype == "risk_severity_present":
        ok = any(r["severity"] == check["severity"] for r in risks)
        return ("PASS" if ok else "FAIL"), f"severites observees={[r['severity'] for r in risks]}"

    if ctype == "risk_title_contains":
        ok = any(check["keyword"].lower() in r["title"].lower() for r in risks)
        return ("PASS" if ok else "FAIL"), f"titres observes={[r['title'] for r in risks]}"

    if ctype == "no_high_risk_missing_titre":
        ok = not any("titre de propriete" in r["title"].lower() and r["severity"] == "eleve" for r in risks)
        return ("PASS" if ok else "FAIL"), f"titres observes={[r['title'] for r in risks]}"

    facts = result.get("document_facts", [])

    if ctype == "fact_contains":
        ok = any(f["field_name"] == check["field_name"] for f in facts)
        return ("PASS" if ok else "FAIL"), f"field_names observes={[f['field_name'] for f in facts]}"

    if ctype == "vision_disclaimer_present":
        ok = any(f["field_name"] == "vision_disclaimer" for f in facts)
        return ("PASS" if ok else "FAIL"), f"field_names observes={[f['field_name'] for f in facts]}"

    return "FAIL", f"type de check inconnu : {ctype}"


def run_all() -> list[dict]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    case_files = sorted(CASES_DIR.glob("case_*.json"))
    report = []

    for case_file in case_files:
        case = json.loads(case_file.read_text(encoding="utf-8"))
        case_id = case["case_id"]
        print(f"--- {case_id} ---")

        disabled = case.get("disable_service")
        if disabled:
            print(f"  arret du service '{disabled}' pour simuler une panne...")
            _docker("stop", disabled)
            time.sleep(2)

        start = time.perf_counter()
        try:
            status, result = _submit_case(case)
        finally:
            if disabled:
                print(f"  redemarrage du service '{disabled}'...")
                _docker("start", disabled)
                time.sleep(5)  # let the restarted service finish binding before the next case hits it
        duration_s = time.perf_counter() - start

        (RESULTS_DIR / f"{case_id}.json").write_text(
            json.dumps({"status": status, "result": result}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        checks_report = []
        for check in case["expected_checks"]:
            verdict, detail = _run_check(check, status, result)
            checks_report.append({"check": check, "verdict": verdict, "detail": detail})
            print(f"  [{verdict}] {check['type']} — {detail[:120]}")

        report.append(
            {
                "case_id": case_id,
                "category": case["category"],
                "description": case["description"],
                "status": status,
                "duration_s": round(duration_s, 1),
                "checks": checks_report,
            }
        )

    return report


def write_markdown_report(report: list[dict]) -> None:
    total_duration = sum(r["duration_s"] for r in report)

    # Computed early so the English summary (below) can report final numbers
    # without duplicating the per-case loop that also builds the French detail.
    _pass = _fail = _info = 0
    for _r in report:
        _verdicts = [c["verdict"] for c in _r["checks"]]
        _pass += _verdicts.count("PASS")
        _fail += _verdicts.count("FAIL")
        _info += _verdicts.count("INFO")

    lines = [
        "# Evaluation Results — DealPilot AI",
        "",
        "*(English summary below; the detailed per-case results further down are the live "
        "system's own French-language output — the target user works in French, see "
        "`docs/case_study.md`.)*",
        "",
        f"Ran on {len(report)} synthetic cases (`data/synthetic_cases/`) against the real system "
        "running locally (`docker compose up`), including 9 adversarial scenarios matching the "
        "failure modes identified in the original brief (contradictions, missing documents, broken "
        "URL, implausible rent, ambiguous visual defect, incompatible surfaces, service outage, "
        "unprofitable financing, prompt injection).",
        "",
        f"**Result: {_pass} checks passed, {_fail} failed, {_info} documented known limitation(s).** "
        f"Average duration per case: {round(total_duration / len(report), 1)}s.",
        "",
        "**Baseline vs system**: no real timed human trial was run (solo sprint, no access to a "
        "real investor for a blind test) — the baseline is a qualitative estimate from the manual "
        "workflow documented in `docs/case_study.md` (several hours per deal, spread over several "
        "days). The system's measured time covers automated calculation only, not the investor's "
        "human review of the result — which stays necessary and voluntary (the system never "
        "decides). See `docs/case_study.md` for why this baseline comparison is not presented as "
        "proof.",
        "",
        "**What this test pass found and fixed**: a real bug (`case_09`, a `market` service outage "
        "crashed the whole pipeline with a 500 error instead of degrading gracefully) — fixed, then "
        "the same safety net was extended preemptively to 6 other steps with the same untested "
        "weakness. One known limitation was found and left undone: no rule detects an implausible "
        "rent vs market price — deferred to `docs/iteration_plan.md`.",
        "",
        "---",
        "",
        "# Résultats d'évaluation — DealPilot AI (détail, sortie système en français)",
        "",
        f"Exécuté sur {len(report)} cas synthétiques (`data/synthetic_cases/`), contre le système ",
        "réel tournant en local (`docker compose up`), y compris 9 scénarios adverses correspondant ",
        "aux modes de panne identifiés dans le brief d'origine (contradictions, documents manquants, ",
        "URL cassée, loyer implausible, indice visuel ambigu, surfaces incompatibles, panne de service, ",
        "financement non viable, injection de prompt). Résultats bruts par cas dans `eval/results/`.",
        "",
        "## Baseline vs système",
        "",
        "**Baseline** : non mesurée par un essai humain chronométré réel (contrainte de ce sprint mené "
        "en solo, pas d'accès à un vrai investisseur pour un test à l'aveugle). Estimation qualitative "
        "à partir du flux manuel documenté dans `docs/case_study.md` : plusieurs heures par dossier "
        "(collecte de documents, lecture, modélisation Excel), réparties sur plusieurs jours.",
        "",
        f"**Système** : {round(total_duration / len(report), 1)}s en moyenne par dossier pour "
        "l'exécution automatisée complète du pipeline en 10 étapes (documents, vision, marché, "
        "finance, risques, offre, due diligence). Ce chiffre couvre le calcul, pas la revue humaine "
        "du résultat par l'investisseur — qui reste nécessaire et volontaire (le système ne décide "
        "jamais). La réduction porte sur le temps de collecte/analyse mécanique, pas sur le jugement final.",
        "",
        "## Résumé",
        "",
        "| Cas | Catégorie | Statut HTTP | Durée | Résultat |",
        "|---|---|---|---|---|",
    ]
    total_pass = total_fail = total_info = 0
    for r in report:
        verdicts = [c["verdict"] for c in r["checks"]]
        n_pass = verdicts.count("PASS")
        n_fail = verdicts.count("FAIL")
        n_info = verdicts.count("INFO")
        total_pass += n_pass
        total_fail += n_fail
        total_info += n_info
        overall = "✅" if n_fail == 0 else "❌"
        lines.append(
            f"| {r['case_id']} | {r['category']} | {r['status']} | {r['duration_s']}s | "
            f"{overall} {n_pass} pass / {n_fail} fail / {n_info} info |"
        )

    lines += [
        "",
        f"**Total : {total_pass} vérifications passées, {total_fail} échouées, "
        f"{total_info} limitations connues documentées.**",
        "",
        "## Détail par cas",
        "",
    ]
    for r in report:
        lines.append(f"### {r['case_id']} ({r['category']})")
        lines.append("")
        lines.append(r["description"])
        lines.append("")
        lines.append(f"Statut HTTP : `{r['status']}` — durée : {r['duration_s']}s")
        lines.append("")
        for c in r["checks"]:
            icon = {"PASS": "✅", "FAIL": "❌", "INFO": "ℹ️"}[c["verdict"]]
            lines.append(f"- {icon} **{c['check']['type']}** — {c['detail']}")
        lines.append("")

    lines += [
        "## Ce que cette passe de tests a trouvé et corrigé",
        "",
        "- **Bug réel trouvé** (`case_09_adversarial_simulated_api_outage`) : une panne du service "
        "`market` faisait planter tout le pipeline avec une erreur 500, alors que toutes les autres "
        "étapes dégradaient déjà gracieusement. Corrigé dans `services/orchestrator/app/graph.py` "
        "avec le même filet de sécurité (capture l'échec, ajoute un fait d'erreur, continue).",
        "- **Durcissement préventif** : le même filet de sécurité manquait aussi sur 6 autres étapes "
        "(document-intel, vision, financial-engine, risk, offer, due-diligence) qui n'avaient jamais "
        "été testées en panne. Corrigé de façon identique, avant qu'un incident réel ne le révèle.",
        "- **Limitation découverte, non corrigée** (`case_06_adversarial_abnormal_rent`) : aucune règle "
        "ne détecte un loyer implausible par rapport au marché — un loyer irréaliste produit des "
        "chiffres flatteurs sans avertissement. Reporté dans `docs/iteration_plan.md`.",
        "",
    ]

    (ROOT / "docs" / "eval_results.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapport ecrit dans docs/eval_results.md : {total_pass} pass, {total_fail} fail, {total_info} info.")


if __name__ == "__main__":
    write_markdown_report(run_all())
