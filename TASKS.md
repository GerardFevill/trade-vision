# Trade Vision — Backlog

## En cours
- [ ] Intégration cTrader (fichiers non committés : `ctrader_client.py`, `ctrader_service.py`, `ctrader_accounts.py`)
- [ ] Scripts backend utilitaires (`backend/scripts/` non committé)
- [ ] Configuration proxy frontend (`proxy.conf.json` non committé)

## A faire
- [ ] Créer `docs/SPEC.md` — Spécification complète du projet
- [ ] Tests unitaires backend (couverture à améliorer)
- [ ] Tests frontend (pas de tests détectés)
- [ ] Gérer les erreurs de connexion MT5 côté frontend
- [ ] Notifications temps réel via WebSocket
- [ ] Amélioration du système d'alertes
- [ ] Pagination des trades et historiques
- [ ] Gestion des rôles utilisateurs (multi-utilisateur)
- [ ] Documentation API (Swagger/OpenAPI)

## Fait (v1.2.0)
- [x] Dashboard multi-comptes MT5
- [x] Détail de compte avec graphiques
- [x] Gestion des portefeuilles
- [x] Calcul de drawdown et métriques de risque
- [x] Export Excel
- [x] Bridge MT5 pour Docker
- [x] CI/CD GitHub Actions
- [x] Conteneurisation Docker complète
- [x] UI MQL5-inspired redesign
- [x] Bouton de sync MT5 temps réel
