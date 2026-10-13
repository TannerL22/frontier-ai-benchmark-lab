# Follow-up source review — 13 October 2026

All 153 observations labelled inherited in v5.2 were investigated through their primary publishers. The factual capture ledger and source representation digests are in `source_review_2026_10_13.json`. Reader captures are retained locally outside Git; browser table captures provide the AA comparison values. These are captured representations, not original HTML archives or exact original run logs.

| Disposition | Count |
| --- | ---: |
| Stored number corroborated | 148 |
| Current AA number differs | 4 |
| Current leaderboard represents a different date/population | 1 |
| Not investigated in this follow-up | 0 |

The [AA comparison table](https://artificialanalysis.ai/models/comparisons?compare=claude-opus-5-5%2Cgpt-6-astra%2Cgpt-6-1-sol%2Cclaude-fable-5-1%2Cclaude-sonnet-5-5) now reports Astra Briefcase 1571 (previously 1570), Sol Briefcase 1561 (1557), Astra GDPval 1572 (1574), and Sol GDPval 1593 (1592). v5.3 records these as dated current-source revisions. The available artifacts do not establish whether the older difference was transcription error or later publisher revision. v5.2 and the registered forecast inputs retain the old values.

[Arena's current overall table](https://arena.ai/leaderboard/chat/text?scoring=raw) is dated October 13 and reports Astra Max 1442, while the stored row describes the October 8 population and records 1440. The newer population does not verify the older one. That one historical value remains individually uncorroborated; it is not silently replaced or represented as a proven error.

The Vals model profiles corroborate the inherited professional-task values and report default provider/settings and uncertainty displays. [Vals methodology](https://www.vals.ai/methodology) describes task-level or run-level standard errors depending on evaluation design; these do not capture all prompt/seed/deployment variability. v5.3 preserves reported values and uncertainty type instead of drawing generic confidence bars. KSP's displayed zero is left uninterpreted as a population interval. [Opus's profile](https://www.vals.ai/models/anthropic_claude-opus-5-5) also documents refusal fallbacks to Opus 5 and Opus 4.8; benchmark-specific fallback treatment matters. Default profile settings do not certify every original run's conditions.

The follow-up also checked the missing Epoch Fable/Sonnet values against their own model scorecards. The parser checks the labelled model column, rather than a comparison's best-score annotation. The exact endpoints, original run IDs, harness versions and resource budgets are still incomplete. Numeric corroboration is a narrower result than run comparability.

The v5.3 portfolio therefore has 305 numerically corroborated or reconstructed included values and one explicit unresolved historical-population value. Five reconstructions retain their rounded-component status; provisional publisher labels remain provisional. All releases and decisions are versioned. This source review is internal Codex curation; the project owner's independent review concerns pilot task validity and future-outcome eligibility and is not falsely marked complete here.
