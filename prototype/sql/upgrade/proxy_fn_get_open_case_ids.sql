CREATE OR REPLACE FUNCTION get_open_case_ids(domain text, owner_id uuid) RETURNS SETOF uuid AS $$
    CLUSTER cluster_for_domain(domain);
    RUN ON ALL;
    SELECT id FROM case_data WHERE case_data.domain = $1 AND case_data.owner_id = $2 AND case_data.closed = false;
$$ LANGUAGE plproxy;
