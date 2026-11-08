-- Adzuna now searches India only (LinkedIn via Apify covers other countries).
-- Remove the unranked Adzuna-only listings from other countries. Jobs the user
-- has saved, applied to or dismissed, and any job also found on LinkedIn, are kept.
DELETE FROM jobs
WHERE status = 'new'
  AND country <> 'in'
  AND sources NOT LIKE '%"apify"%';
