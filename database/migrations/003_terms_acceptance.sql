BEGIN;
ALTER TABLE users ADD COLUMN terms_accepted_at bigint;
COMMIT;
