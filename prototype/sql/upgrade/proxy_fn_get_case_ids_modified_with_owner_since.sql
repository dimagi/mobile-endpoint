CREATE OR REPLACE FUNCTION get_case_ids_modified_with_owner_since(domain text, owner_id uuid, reference_date timestamp with time zone) RETURNS SETOF uuid AS $$
    CLUSTER cluster_for_domain(domain);
    RUN ON ALL;
    SELECT id FROM case_data WHERE case_data.domain = $1 AND case_data.owner_id = $2 AND case_data.server_modified_on > $3;
$$ LANGUAGE plproxy;
