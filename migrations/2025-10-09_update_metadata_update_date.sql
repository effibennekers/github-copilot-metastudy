-- Migratie: Zet metadata.update_date om van TEXT naar DATE zonder lange locks
-- Strategie: extra kolom + trigger + batch backfill + snelle kolom-swap

-- 1) Voeg nieuwe DATE-kolom toe
ALTER TABLE metadata ADD COLUMN IF NOT EXISTS update_date_new DATE;

-- 2) Triggerfunctie om nieuwe records synchroon te zetten
CREATE OR REPLACE FUNCTION metadata_update_date_sync() RETURNS trigger AS $$
BEGIN
  IF NEW.update_date IS NOT NULL THEN
    NEW.update_date_new := to_date(split_part(NEW.update_date, 'T', 1), 'YYYY-MM-DD');
  ELSE
    NEW.update_date_new := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3) Trigger op INSERT/UPDATE van update_date
DROP TRIGGER IF EXISTS metadata_update_date_sync_trg ON metadata;
CREATE TRIGGER metadata_update_date_sync_trg
BEFORE INSERT OR UPDATE OF update_date ON metadata
FOR EACH ROW EXECUTE FUNCTION metadata_update_date_sync();

-- 4) Optioneel: maak alvast een index op de nieuwe kolom (CONCURRENTLY moet los gedraaid worden)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metadata_update_date_new ON metadata(update_date_new);

-- 5) Backfill in batches om lange locks te vermijden
DO $$
DECLARE
  batch_size integer := 50000;  -- pas aan indien nodig
  rows_updated integer;
BEGIN
  LOOP
    UPDATE metadata m
    SET update_date_new = to_date(split_part(m.update_date, 'T', 1), 'YYYY-MM-DD')
    WHERE m.update_date_new IS NULL
      AND m.update_date IS NOT NULL
      AND m.id IN (
        SELECT id FROM metadata
        WHERE update_date_new IS NULL AND update_date IS NOT NULL
        LIMIT batch_size
      );

    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    EXIT WHEN rows_updated = 0;
    PERFORM pg_sleep(0.1); -- korte pauze tussen batches
  END LOOP;
END $$;

-- 6) Snelle swap van kolommen (korte lock window)
ALTER TABLE metadata RENAME COLUMN update_date TO update_date_text;
ALTER TABLE metadata RENAME COLUMN update_date_new TO update_date;

-- 7) Maak index op de nieuwe DATE-kolom (los, want CONCURRENTLY mag niet in transaction blocks)
-- Aanbevolen volgorde buiten transacties:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metadata_update_date_date ON metadata(update_date);
-- (optioneel) DROP INDEX CONCURRENTLY IF EXISTS idx_metadata_update_date; -- oude index op text-kolom kan nu weg of hernoemd

-- 8) Opruimen: trigger en functie verwijderen
DROP TRIGGER IF EXISTS metadata_update_date_sync_trg ON metadata;
DROP FUNCTION IF EXISTS metadata_update_date_sync();

-- 9) (optioneel) Verwijder oude text-kolom na validatie
-- ALTER TABLE metadata DROP COLUMN update_date_text;


