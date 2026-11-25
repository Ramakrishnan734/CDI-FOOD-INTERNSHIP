BEGIN;

ALTER TABLE items
    ADD COLUMN IF NOT EXISTS selling_price NUMERIC(15,2);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_item_selling_price_positive'
          AND conrelid = 'items'::regclass
    ) THEN
        ALTER TABLE items
            ADD CONSTRAINT chk_item_selling_price_positive
            CHECK (
                selling_price IS NULL
                OR selling_price > 0
            );
    END IF;
END
$$;

DO $$
DECLARE
    total_matches INTEGER;
    finished_matches INTEGER;
BEGIN
    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE item_type = 'finished')
    INTO total_matches, finished_matches
    FROM items
    WHERE code = 'FG-MRK200';

    IF total_matches <> 1 THEN
        RAISE EXCEPTION
            'Expected exactly one FG-MRK200 row; found %',
            total_matches;
    END IF;

    IF finished_matches <> 1 THEN
        RAISE EXCEPTION
            'FG-MRK200 must exist exactly once as a finished item';
    END IF;
END
$$;

UPDATE items
SET selling_price = 50.00
WHERE code = 'FG-MRK200'
  AND item_type = 'finished'
  AND selling_price IS NULL;

DO $$
DECLARE
    total_matches INTEGER;
    finished_matches INTEGER;
    configured_matches INTEGER;
BEGIN
    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE item_type = 'finished'),
           COUNT(*) FILTER (WHERE selling_price IS NOT NULL)
    INTO total_matches, finished_matches, configured_matches
    FROM items
    WHERE code = 'FG-MRK200';

    IF total_matches <> 1
       OR finished_matches <> 1
       OR configured_matches <> 1 THEN
        RAISE EXCEPTION
            'FG-MRK200 must exist exactly once as a finished item with a configured selling price';
    END IF;
END
$$;

COMMIT;
