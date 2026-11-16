# Smart Internship Match — rapport

*Projet 1, Business Intelligence (ENSIM). Brouillon à relire et compléter : les passages entre crochets [ ] restent à remplir.*

## 1. La décision soutenue

Je cherche un stage de fin d'études de 6 mois en informatique, avec une préférence pour l'intelligence artificielle. Le système répond à deux questions, chaque semaine : **à quelles offres postuler en priorité**, et **quelles compétences me manquent le plus souvent**. Il aide à décider, il ne décide pas : le classement est une aide, le choix de postuler et le suivi des candidatures restent faits à la main (principe *human-in-the-loop*, CM5).

## 2. Architecture du pipeline

| Étape | Outil | Où | Résultat |
|---|---|---|---|
| Acquisition | jobspy (Indeed) | local, à la demande | 30 résultats, 18 stages (16/11) |
| Acquisition (prévue) | API France Travail (OAuth2, secrets GitHub, Action hebdomadaire) | cloud | non branchée : API indisponible pendant le projet |
| Fusion | `merge_offer_sources.py` | local | un schéma commun + un indicateur `publishable` |
| Structuration | Ollama `qwen3:8b` | local | compétences, missions, expérience, rémunération |
| KPI de correspondance | `match_offers.py` | local | score, couverture, atouts, manques, priorité |
| Action | Ollama | local | 3 accroches de lettre de motivation |
| Suivi | `applications.csv` (tenu à la main) | local | candidatures et réponses |
| Surveillance | `monitor.py` | local | 4 vérifications journalisées |
| Restitution | `docs/dashboard.html` | local | tableau de bord |

**Choix d'un dépôt privé.** Mon profil de compétences et mes offres ciblées sont des données personnelles, et les offres scrapées ne doivent pas être redistribuées. Contrepartie : pas de GitHub Pages gratuit, le tableau de bord se consulte en local (`python -m http.server`). Le `.gitignore` a été créé avant toute donnée et reste en place malgré le dépôt privé (protection contre un passage en public ou un collaborateur).

## 3. Données, provenance et risques

- **France Travail** est une donnée publique sous licence de réutilisation : publiable. Son API était indisponible au démarrage du projet ; le pipeline a été adapté pour **continuer quand une source manque** (`load_france_travail()` signale l'absence au lieu de planter).
- **Indeed via jobspy** : les conditions d'utilisation interdisent le scraping et la redistribution. Mesures prises : exécution locale et ponctuelle uniquement, LinkedIn exclu (plateforme qui poursuit ce type d'usage), offres marquées `publishable: false`, fichiers ignorés par Git, jamais publiés.
- **ZipRecruiter** a échoué à chaque exécution (HTTP 307) : ce site ne couvre pas la France.
- Bilan : **1 source sur 3 fonctionnelle** pendant le projet, d'où l'intérêt d'un pipeline multi-sources tolérant aux pannes.

## 4. L'IA : où elle sert, et ses erreurs

L'IA n'intervient que là où l'information est enfouie dans du texte libre (compétences, missions, expérience, rémunération) et pour rédiger des brouillons. Titre, entreprise et lieu sont déjà des champs structurés : on ne les lui demande pas (CM5).

Deux ajustements par rapport au code fourni, tirés des TD : désactivation de la phase de « réflexion » de `qwen3` (`"think": false`), qui ralentissait fortement les appels ; et envoi du **texte complet** des offres (au TD3, une coupure à 1 500 caractères avait fait disparaître des compétences et sous-estimé un KPI de moitié).

**Erreurs relevées en relisant la sortie contre le texte d'origine** (`data/quality/extraction_review.csv`) :

| Offre | Erreur | Type |
|---|---|---|
| Q Energy | « Power BI » extrait alors que l'offre ne parle que de « tableaux de bord » | hallucination |
| Natixis | « 60 % » pris pour un salaire (remboursement du transport) | mauvaise valeur |
| Efinor | « 35 heures hebdomadaires » pris pour un salaire | mauvaise valeur |
| Sogeclair | « RTT, mutuelle… » donné comme rémunération, sans chiffre | consigne ignorée |
| GERFLOR | même compétence extraite deux fois (casse différente) | doublon |
| ABB | seulement « IA, data science, informatique » : aucun outil concret | trop vague |
| Sopra Steria (lettre) | « comprendre les contraintes des systèmes robotiques » : rien dans mon profil ne le justifie | exagération à la rédaction |

Sur le premier lot (3/11), 3 des 6 « rémunérations » trouvées étaient fausses ; seules 3 offres sur 14 indiquaient réellement un montant. La rémunération est donc rarement exploitable : elle est affichée comme un simple compte, pas comme un graphique. Sur le second lot (16/11), les 3 rémunérations extraites étaient exactes.

## 5. Le KPI de correspondance

- **Couverture** = acquises / (acquises + ⅓ × manquantes). Une compétence manquante pèse trois fois moins qu'une compétence acquise : un stage sert aussi à apprendre, et les offres listent souvent des compétences « souhaitées ». Exemple : 2 compétences sur 4 donnent 75 %, et non 50 %.
- **Score** = 100 × couverture × (0,8 + 0,2 × niveau moyen / 5). Mon niveau auto-évalué affine le score (au plus −20 %) sans jamais renverser le classement.
- **Comparaison des noms** : normalisation (casse, accents, apostrophes), recherche du mot entier (« Git » ne correspond pas à « GitHub »), et un petit dictionnaire de synonymes (« intégration continue » = CI/CD). Limite assumée : un synonyme imprévu n'est pas reconnu.
- **Offres sans compétence extraite** : mises à part (`scorable: false`), jamais confondues avec de mauvaises offres, jamais de lettre générée.
- **Préférence IA, séparée de l'adéquation** : la *priorité* vaut score + 15 points si l'offre relève de l'IA (plafonnée à 100). Le score d'adéquation reste intact, pour ne pas mélanger « je corresponds » et « cela m'intéresse » dans un seul chiffre (CM2).

**Effet des décisions, mesuré sur le même lot d'offres (3/11)** : ABB, « Intégration de l'IA », passe de 0 à 79 une fois mes compétences IA et data ajoutées au profil ; les 5 premières offres deviennent toutes des offres IA.

**Un bug trouvé en relisant le classement** : l'apostrophe typographique de « d’IA » était supprimée avant d'être convertie, si bien que l'offre Sopra Steria « Optimisation de modèles d’IA » n'était pas reconnue comme offre IA. Une fois corrigé, elle passe première (priorité 100).

**Classement actuel (16/11, 18 offres)** : 1. Sopra Steria, optimisation de modèles d'IA (100) ; 2. ENGIE, stagiaire IA (94) ; 3. Air France, Data Science (93) ; 4. Société Générale, FinOps data (84) ; 5. LYNRED, cybersécurité (79). Compétences manquantes récurrentes : Power BI, VBA, PowerPoint, Java.

## 6. Le tableau de bord et le choix des graphiques

Pour : moi. Décision : où postuler cette semaine, et quoi apprendre.

| Élément | Catégorie de KPI | Pourquoi cette forme |
|---|---|---|
| Classement des offres | efficacité de la recherche | **tableau**, pas un graphique : j'agis offre par offre, il me faut le nom, le score exact et ce qui manque |
| Compétences manquantes | efficacité de la recherche | **barres horizontales triées** : un classement de fréquences entre catégories ; horizontal parce que les noms sont longs ; pas de camembert, qui compare mal des parts proches |
| Tuiles chiffrées (offres, offres IA, bonnes offres, atout le plus demandé) | efficacité | une valeur unique se lit mieux en chiffre qu'en graphique |
| État des sources, erreurs de l'IA | santé du pipeline | tableaux d'état : chaque ligne est OK ou en échec, avec sa raison |
| Candidatures, taux de réponse, sans réponse > 10 jours | résultats | un KPI qui n'est pas « plus de candidatures » : le taux de réponse dit si la recherche est bien ciblée |
| Journal de surveillance | surveillance | historique des vérifications, une ligne par exécution |

## 7. Surveillance

`monitor.py` vérifie : candidatures sans réponse depuis plus de 10 jours, offres périmées (plus de 7 jours), sources en échec, bonnes offres (priorité ≥ 50) sans candidature.

- **16/11, 15h00** : alerte « offres périmées » (13 jours), sources en échec (France Travail, ZipRecruiter), bonnes offres non traitées.
- Action : nouvelle collecte (18 stages), extraction et classement relancés.
- **16/11, 15h12** : « offres périmées » repasse à OK ; les sources en échec et les candidatures à envoyer restent signalées.

Incident non prévu : lors de la relance, Ollama n'était pas démarré et toute l'extraction s'est arrêtée dès la première offre. Amélioration possible : vérifier qu'Ollama répond avant de lancer l'extraction.

## 8. Résultats des candidatures

[À compléter : candidatures envoyées, réponses, entretiens, taux de réponse, et ce que la surveillance « sans réponse depuis 10 jours » a détecté.]

## 9. Limites et suites

- La population d'offres dépend d'un seul mot-clé (« stage informatique ») : beaucoup de bruit (marketing, maintenance industrielle). Piste : plusieurs recherches ciblées (IA, data, développement).
- Le KPI dépend entièrement de la qualité de l'extraction (une offre IA décrite sans outil concret obtient un score bas).
- Profil auto-évalué : niveaux subjectifs ; certaines compétences courantes (Windows, Excel) sont déclarées sans preuve détaillée.
- France Travail à brancher dès que l'API est disponible [date].
