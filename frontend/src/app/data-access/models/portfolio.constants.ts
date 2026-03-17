export type PortfolioType = 'Securise' | 'Conservateur' | 'Modere' | 'Agressif';

export const PORTFOLIO_TYPES: Record<PortfolioType, number[]> = {
  Securise: [],  // Pas de facteur - nombre illimite de comptes
  Conservateur: [0.2, 0.6, 1.0, 1.4, 1.8],
  Modere: [2.0],
  Agressif: [2.5, 3.0, 3.5, 4.0, 4.5],
};

export const LOT_FACTORS = [0.2, 0.6, 1.0, 1.4, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5];

// Withdrawal percentages by type
export const WITHDRAWAL_PERCENTAGES: Record<string, number> = {
  Securise: 50,
  Conservateur: 70,
  Modere: 80,
  Agressif: 90,
};
