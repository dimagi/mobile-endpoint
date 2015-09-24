DROP TYPE IF EXISTS case_index_row;
CREATE TYPE case_index_row AS (identifier text, referenced_id uuid, referenced_type text, is_new boolean);

CREATE OR REPLACE FUNCTION create_or_update_case_indices(domain text, case_id text, indices case_index_row[]) RETURNS integer AS $$
DECLARE
    i int:
    cnt int := 0;
    index case_index_row;
BEGIN
    FOREACH index IN ARRAY indices
    LOOP
        IF index.is_new THEN
            INSERT INTO case_index (
                case_id,
                domain,
                identifier,
                referenced_id,
                referenced_type)
            VALUES ($1::uuid, index.domain, index.identifier, index.referenced_id, index.referenced_type);
        ELSE
            UPDATE case_index
            SET identifier= index.identifier, referenced_id = index.referenced_id, referenced_type = index.referenced_type
            WHERE case_id = $1::uuid;
        END IF;
        GET DIAGNOSTICS i = ROW_COUNT;
        cnt := cnt + i;
    END LOOP;
    RETURN cnt;
END;
$$ LANGUAGE plpgsql;
