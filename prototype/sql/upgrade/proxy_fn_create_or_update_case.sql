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
        CLUSTER 'hqcluster';
        RUN ON hashtext(case_id);
$$ LANGUAGE plproxy;
