CREATE OR REPLACE FUNCTION create_or_update_case(
    case_id text,
    domain text,
    closed boolean,
    owner_id text,
    server_modified_on timestamp,
    version integer,
    case_json jsonb,
    attachments jsonb,
    is_new boolean) RETURNS integer AS $$
    DECLARE
        cnt int;
    BEGIN
        IF is_new THEN
            INSERT INTO case_data (
                id,
                domain,
                closed,
                owner_id,
                server_modified_on,
                version,
                case_json,
                attachments)
            VALUES ($1::uuid, $2, $3, $4::uuid, $5, $6, $7, $8);
        ELSE
            UPDATE case_data
            SET closed = $3, owner_id = $4::uuid, server_modified_on = $5, version = $6, case_json = $7, attachments = $8
            WHERE id = $1::uuid;
        END IF;
        GET DIAGNOSTICS cnt = ROW_COUNT;
        RETURN cnt;
    END;
$$ LANGUAGE plpgsql;
