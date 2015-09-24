CREATE OR REPLACE FUNCTION get_case_by_id(domain text, case_id text)
RETURNS SETOF case_data AS $$
    CLUSTER cluster_for_domain(domain);
    RUN ON hashtext(case_id);
    SELECT * FROM case_data WHERE id = $1::uuid;
$$ LANGUAGE plproxy;
