CREATE OR REPLACE FUNCTION insert_form(
    form_id text,
    domain text,
    received_on timestamp,
    user_id text,
    md5 text,
    synclog_id text,
    attachments jsonb) RETURNS integer AS $$
    DECLARE
        cnt int;
    BEGIN
        INSERT INTO form_data (
            id,
            domain,
            received_on,
            user_id,
            md5,
            synclog_id,
            attachments)
        VALUES ($1::uuid, $2, $3, $4::uuid, $5::bytea, $6::uuid, $7);
        GET DIAGNOSTICS cnt = ROW_COUNT;
        RETURN cnt;
    END;
$$ LANGUAGE plpgsql;
