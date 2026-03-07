# Elite Monitor - Backlog

## Terminé

- [x] Intégration cTrader Open API (Protobuf over TCP/TLS)
- [x] Détection copy trading via scan CashFlowHistory
- [x] Champs `copy_invested` / `copy_strategy` (modèle -> DB -> API -> frontend)
- [x] Badge copy sur les cartes et le tableau
- [x] Rebranding MT5 -> Elite Monitor (sidebar, headers, i18n)

## En cours

- [ ] Tests end-to-end de l'intégration cTrader
- [ ] Validation des données copy trading sur comptes réels

## À faire

- [ ] Optimiser `_scan_cashflow()` (cache, pagination moins agressive)
- [ ] Gestion du refresh token cTrader (expiration OAuth2)
- [ ] Affichage copy trading dans la page détail du compte
- [ ] Dashboard unifié MT5 + cTrader (agrégation des totaux)
- [ ] CI/CD : GitHub Actions pipeline
- [ ] Déploiement Docker Compose complet
