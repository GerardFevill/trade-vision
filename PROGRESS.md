# Elite Monitor - Progression

## Feature en cours : cTrader Integration

**Branche** : `feature/ctrader-integration`
**Statut** : En cours

### Historique

| Date | Action | Détail |
|------|--------|--------|
| 2025-03-06 | feat(ctrader) | Intégration initiale cTrader Open API |
| 2025-03-06 | fix(ctrader) | Migration vers Protobuf over TCP |
| 2025-03-07 | feat(ctrader) | Détection copy trading + rebranding Elite |

### Ce qui fonctionne

- Connexion cTrader via Protobuf/TLS (live.ctraderapi.com:5035)
- Récupération comptes, balances, equity, positions
- Détection automatique des investissements copy (opType 30/33)
- Calcul du solde effectif (balance libre + copy investi)
- Affichage badge copy sur la page comptes (grille + tableau)
- Branding "Elite Monitor" unifié

### Points restants

- Optimisation performance scan cashflow (comptes anciens)
- Gestion refresh token OAuth2
- Tests e2e complets
- Merge vers master après validation
