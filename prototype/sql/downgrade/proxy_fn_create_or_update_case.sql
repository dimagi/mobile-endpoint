DROP FUNCTION IF EXISTS create_or_update_case(
    case_id text,
    domain text,
    closed boolean,
    owner_id text,
    server_modified_on timestamp,
    version integer,
    case_json jsonb,
    attachments jsonb,
    is_new boolean);
