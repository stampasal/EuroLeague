// ============================================================
// CONFIG — ρυθμίσεις της εφαρμογής
// Άλλαξέ τες εδώ, όχι μέσα στον κώδικα
// ============================================================
const CONFIG = {
  // Σεζόν
  season: "2026-27",
  totalRounds: 38,

  // Ζώνες κατάταξης
  playoffTeams: 6,      // Top 6 → Playoffs (πράσινο)
  playInTeams: 10,      // 7-10 → Play-In (πορτοκαλί)

  // Εμφάνιση
  scoreInputEnabled: true,   // false → τα score inputs γίνονται readonly
  showL10: true,             // false → κρύβει τη στήλη L10

  // Games view
  defaultRound: 1,           // με ποιο round ξεκινάει το scroll
  autoAdvanceRound: false,   // true → μετά από κάθε αποτέλεσμα, πάει στο επόμενο round

  // Storage
  storageKey: "euroleague-tracker-3.0",
  themeKey: "euroleague-theme"
};