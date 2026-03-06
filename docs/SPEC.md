# Trade Vision — Spécification

> **Statut** : Brouillon — A compléter et valider par l'utilisateur

## 1. Objectif
Application web de monitoring temps réel pour comptes de trading MetaTrader 5 et cTrader.
Permet de suivre la performance, le risque et les drawdowns de plusieurs comptes simultanément.

## 2. Utilisateurs cibles
- Traders particuliers gérant plusieurs comptes MT5/cTrader
- Gestionnaires de portefeuilles multi-comptes

## 3. Fonctionnalités principales

### 3.1 Gestion des comptes
- Connexion à plusieurs comptes MT5 et cTrader
- Affichage du solde, equity, marge en temps réel
- Historique des trades par compte

### 3.2 Dashboard
- Vue d'ensemble de tous les comptes connectés
- Métriques clés : balance, equity, profit/perte, drawdown
- Graphiques d'évolution (Chart.js)

### 3.3 Analytics
- Statistiques de trading (win rate, ratio risque/récompense)
- Analyse des drawdowns (max drawdown, drawdown actuel)
- Métriques de risque

### 3.4 Portefeuilles
- Regroupement de comptes en portefeuilles
- Performance agrégée par portefeuille
- Records mensuels

### 3.5 Alertes
- Alertes sur seuils de drawdown
- Notifications de changements significatifs

### 3.6 Export
- Export des données en format Excel

## 4. Architecture technique

### 4.1 Frontend
- Angular 21 + TypeScript
- Chart.js pour les graphiques
- SCSS pour le styling
- Nginx en production

### 4.2 Backend
- FastAPI (Python 3.11)
- Pydantic pour la validation
- PostgreSQL 16 pour la persistance
- Bridge Windows pour MT5

### 4.3 Infrastructure
- Docker Compose (3 services : frontend, backend, postgres)
- CI/CD via GitHub Actions
- Images Docker sur Docker Hub (amesika2)

## 5. Contraintes
- MT5 ne fonctionne que sous Windows (d'où le bridge)
- Les credentials ne doivent jamais être committés
- L'application doit supporter le mode hors-ligne (données en cache)

## 6. A compléter
- [ ] Diagrammes d'architecture
- [ ] Maquettes UI détaillées
- [ ] Spécifications API détaillées
- [ ] Plan de déploiement production
- [ ] Stratégie de tests
