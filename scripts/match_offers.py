import csv, json, os, re, time, unicodedata

# ---------------------------------------------------------------------------
# Match KPI -- design choices (Step 13, "Your task"):
#
# 1. A missing skill weighs 3x less than a skill I have (MISSING_WEIGHT = 1/3):
#    an internship is also for learning, and offers often list "nice to have"
#    skills. With 2 of 4 skills matched: 2 / (2 + 2/3) = 0.75 coverage.
# 2. My self-assessed level only refines the score (factor between 0.8 and 1.0),
#    it never reverses the ranking on its own.
# 3. Skill names are compared after normalization (case, accents, spaces), as
#    whole words inside the extracted skill ("scripting en Python" -> Python),
#    plus a small hand-written synonym list (CI/CD = "integration continue"...).
#    Known limit: a synonym nobody thought of is not recognized.
# 4. An offer with no extracted skill can't be scored: score 0, coverage 0 and
#    "scorable": False, so it sinks to the bottom, is shown apart on the
#    dashboard, and never gets a cover-letter draft.
# ---------------------------------------------------------------------------

MISSING_WEIGHT = 1 / 3
LEVEL_MIN_FACTOR = 0.8   # level factor goes from 0.8 (level 0) to 1.0 (level 5)

# Extra names under which each profile skill can appear in an offer. The skill's
# own name is always included automatically.
SYNONYMS = {
    "CI/CD": ["integration continue", "deploiement continu", "integration et de deploiement continus",
              "continuous integration", "continuous deployment", "ci/cd pipelines"],
    "Deep Learning": ["apprentissage profond", "reseaux de neurones", "neural networks", "neural network"],
    "React": ["react.js", "reactjs"],
    "JavaScript": ["js"],
    "Node.js": ["node", "nodejs"],
    "SQL": ["mysql", "postgresql", "sql server"],
    "Git": ["gitlab", "github"],
    "API REST": ["api", "rest api", "restful"],
    "OAuth": ["oauth2"],
    "Intelligence artificielle": ["ia", "ai", "artificial intelligence", "ia generative", "generative ai",
                                  "machine learning", "llm", "llms", "apprentissage automatique",
                                  "modeles de langage"],
    "Data Science": ["analyse de donnees", "data analysis", "traitement de donnees", "series temporelles",
                     "data analytics"],
    "Cybersecurite": ["cybersecurity", "securite informatique", "securite des systemes d'information",
                      "securite reseau", "securite des reseaux"],
    "Developpement logiciel": ["developpement informatique", "developpement logiciel", "programmation",
                               "programmation de logiciels", "software development", "software engineering"],
    "Excel": ["microsoft excel"],
}

# Preference, kept separate from the match score: AI is what I'm looking for first,
# but as "a plus", not a deciding factor. An AI offer gets AI_BONUS points added to
# its ranking priority (capped at 100); its match score itself is left untouched.
AI_KEYWORDS = ["ia", "ai", "intelligence artificielle", "artificial intelligence", "machine learning",
               "deep learning", "ia generative", "generative ai", "llm", "llms",
               "apprentissage automatique", "modeles de langage"]
AI_BONUS = 15

def is_ai_offer(offer):
    texts = [offer.get("title") or ""] + (offer.get("required_skills") or []) + (offer.get("responsibilities") or [])
    return any(contains_term(normalize(t), normalize(k)) for t in texts for k in AI_KEYWORDS)

def normalize(text):
    # lowercase, accents removed, curly apostrophes and extra spaces unified.
    # The curly apostrophe must be replaced BEFORE the ASCII conversion, otherwise
    # it is silently dropped ("d'IA" became "dia" and the AI offer wasn't detected).
    text = str(text).replace("’", "'")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()

def contains_term(skill_text, term):
    # whole-word match: "git" must not match "github", "c" must not match "cobol".
    # Word characters here include + and # so that "c++" and "c#" stay whole words.
    return re.search(rf"(?<![\w+#]){re.escape(term)}(?![\w+#])", skill_text) is not None

def load_profile(path="data/profile/my_skills.csv"):
    profile = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            profile[row["skill"]] = {"level": int(row["level"]), "evidence": row["evidence"]}
    return profile

def find_profile_skill(offer_skill, profile):
    """Return the name of the profile skill this offer skill corresponds to, or None."""
    text = normalize(offer_skill)
    for name in profile:
        aliases = [name] + SYNONYMS.get(name, [])
        if any(contains_term(text, normalize(a)) for a in aliases):
            return name
    return None

def score_offer(profile, required_skills):
    # Deduplicate the offer's skills first: the AI sometimes returns the same skill
    # twice with different capitalization (seen on a real GERFLOR offer).
    unique_skills = {}
    for s in required_skills or []:
        unique_skills.setdefault(normalize(s), s)

    if not unique_skills:
        return {"score": 0.0, "coverage": 0.0, "matched": [], "gaps": [],
                "scorable": False, "n_required": 0}

    matched, gaps, n_covered = set(), [], 0
    for original in unique_skills.values():
        found = find_profile_skill(original, profile)
        if found:
            matched.add(found)
            n_covered += 1
        else:
            gaps.append(original)

    coverage = n_covered / (n_covered + MISSING_WEIGHT * len(gaps))
    if matched:
        avg_level = sum(profile[s]["level"] for s in matched) / len(matched)
    else:
        avg_level = 0
    level_factor = LEVEL_MIN_FACTOR + (1 - LEVEL_MIN_FACTOR) * avg_level / 5
    score = 100 * coverage * level_factor

    return {
        "score": round(score, 1),
        "coverage": round(coverage, 3),
        "matched": sorted(matched),
        "gaps": gaps,
        "scorable": True,
        "n_required": len(unique_skills),
    }

def build_output(results, profile):
    gap_counts = {}
    matched_counts = {}
    for r in results:
        for g in r["gaps"]:
            gap_counts[g] = gap_counts.get(g, 0) + 1
        for s in r["matched"]:
            matched_counts[s] = matched_counts.get(s, 0) + 1
    top_gaps = sorted(gap_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top_matched = sorted(matched_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    n_with_comp = sum(1 for r in results if r.get("compensation_mentioned"))
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_offers": len(results),
        "n_unscored": sum(1 for r in results if not r.get("scorable", True)),
        "n_ai_offers": sum(1 for r in results if r.get("is_ai_offer")),
        "ai_bonus": AI_BONUS,
        "offers": results,
        "top_skill_gaps": [{"skill": s, "count": c} for s, c in top_gaps],
        # top_matched_skills mirrors top_skill_gaps but for what you're already
        # strong in -- ranked by how often it's actually asked for across your real
        # offers, with your own self-assessed level attached so the dashboard can
        # highlight "your most in-demand strength", not just "a skill you have".
        "top_matched_skills": [{"skill": s, "count": c, "level": profile[s]["level"]} for s, c in top_matched],
        # Set expectations, don't hide the gap: real testing (see Step 12's note)
        # found compensation stated explicitly in only ~6.5% of real postings, so
        # this is reported as a count, not built into a chart that would mostly be
        # empty space.
        "n_offers_with_compensation": n_with_comp,
    }

def main():
    profile = load_profile()
    with open("data/offers/structured_offers.json", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for offer in data["offers"]:
        m = score_offer(profile, offer["required_skills"])
        ai = is_ai_offer(offer)
        priority = min(100.0, m["score"] + (AI_BONUS if ai and m["scorable"] else 0))
        results.append({**offer, **m, "is_ai_offer": ai, "priority": round(priority, 1)})

    # Ranked by priority (match score + AI bonus), not by the raw score: this order
    # is also what draft_cv.py uses to pick the offers worth a cover letter.
    results.sort(key=lambda r: r["priority"], reverse=True)
    print("  prio  score  AI   offer")
    for r in results:
        flag = "" if r["scorable"] else "  [NOT SCORED: no skill extracted]"
        print(f"  {r['priority']:5.1f}  {r['score']:5.1f}  {'yes' if r['is_ai_offer'] else ' - '}  "
              f"{r['title'][:50]} @ {r['company']}  "
              f"(coverage {r['coverage']:.0%}, matched: {r['matched']}, gaps: {r['gaps']}){flag}")

    # Two outputs, not one: matches_all_local.json (every source, gitignored, for
    # your own eyes only) and docs/data/matches.json (publishable sources only,
    # committed). "publishable" was set in Step 11c -- True for France Travail's
    # official data, False for anything from jobspy (Step 11b).
    os.makedirs("data/offers", exist_ok=True)
    with open("data/offers/matches_all_local.json", "w", encoding="utf-8") as f:
        json.dump(build_output(results, profile), f, indent=2, ensure_ascii=False)
    print(f"Wrote data/offers/matches_all_local.json ({len(results)} offers) -- gitignored, local only")

    public_results = [r for r in results if r.get("publishable", False)]
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/matches.json", "w", encoding="utf-8") as f:
        json.dump(build_output(public_results, profile), f, indent=2, ensure_ascii=False)
    print(f"Wrote docs/data/matches.json ({len(public_results)} of {len(results)} offers -- publishable sources only)")

if __name__ == "__main__":
    main()
