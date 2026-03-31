# Diagnostic Sécurité — Elite Monitor

**Date :** 2026-03-31
**Scope :** Frontend Angular 19 + Backend FastAPI + Docker Compose + Nginx

---

## CRITIQUE (action immédiate)

| # | Problème | Fichier | Impact |
|---|----------|---------|--------|
| 1 | **Aucune authentification API** | `backend/main.py` | Tous les endpoints sont publics — n'importe qui peut lire/modifier les données trading |
| 2 | **CORS trop permissif** | `backend/main.py:48-49` | `allow_methods=["*"]` + `allow_headers=["*"]` + `allow_credentials=True` |
| 3 | **Credentials DB en dur** dans docker-compose | `docker-compose.yml:23-40` | `mt5user:mt5password` en clair, copié partout |
| 4 | **Password par défaut** dans settings | `backend/config/settings.py:31` | `postgres_password: str = "mt5password"` |

## HIGH (court terme)

| # | Problème | Fichier | Impact |
|---|----------|---------|--------|
| 5 | **Pas de security headers** (CSP, X-Frame-Options, HSTS, X-Content-Type-Options) | `frontend/nginx.conf` | Clickjacking, MIME sniffing, XSS |
| 6 | **Pas de HTTPS** | `frontend/nginx.conf` | Données en clair sur le réseau |
| 7 | **Port PostgreSQL exposé** sur l'hôte | `docker-compose.yml:42-43` | Port 10005 accessible avec credentials par défaut |
| 8 | **Erreurs brutes renvoyées au client** | `api/routes/portefeuilles.py:436-438` | `raise HTTPException(500, str(e))` — fuite d'info interne |
| 9 | **Docker : app tourne en root** | `backend/Dockerfile:16` | Pas de `USER` non-root |
| 10 | **Pas de validation format `month`** | `api/routes/portefeuilles.py` (5 endpoints) | Paramètre `str` sans regex `YYYY-MM` |
| 11 | **Dépendances npm vulnérables** | `frontend/package.json` | 27 vulnérabilités (undici, tar, rollup, picomatch) |

## MEDIUM

| # | Problème | Fichier |
|---|----------|---------|
| 12 | **Rate limiting configuré mais pas appliqué** | Routes accounts, portfolios, trades, analytics |
| 13 | **Construction SQL dynamique** avec `f-string` + `.join()` | `db/repositories/alerts.py:149`, `portefeuille_repo.py:212` |
| 14 | **Pas de limite taille requête** | `backend/main.py` |
| 15 | **`print()` au lieu de `logger`** | `db/repositories/growth_cache.py:37,49` |
| 16 | **Codes HTTP incohérents** (503 au lieu de 400/404) | `api/routes/accounts.py`, `analytics.py` |

## Points positifs

- Frontend Angular : pas de `innerHTML`, pas de `bypassSecurityTrust*` — XSS bien géré
- SQL : 95%+ des requêtes sont paramétrées (`%s`)
- `.gitignore` couvre `accounts_local.py`, `ctrader_accounts_local.py`
- Pydantic v2 pour la validation des modèles
- Connection pooling PostgreSQL correct

---

## Plan de remédiation

### Immédiat
1. Restreindre CORS → `allow_methods=["GET","POST","PUT","DELETE"]`, `allow_headers` explicites
2. Sortir les credentials du docker-compose → utiliser `.env` + `env_file:`
3. Ajouter security headers dans nginx
4. Ne plus exposer le port PostgreSQL en prod

### Court terme
5. Implémenter l'authentification (JWT ou API key)
6. Ajouter un `USER` non-root dans le Dockerfile
7. Valider le format `month` avec regex
8. `npm audit fix` pour les dépendances
9. Appliquer le rate limiting sur toutes les routes

### Moyen terme
10. HTTPS avec certificat Let's Encrypt
11. Sanitiser les messages d'erreur renvoyés au client
12. Audit des credentials dans l'historique git
