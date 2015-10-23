CREATE OR REPLACE FUNCTION get_last_modified_dates(domain text, case_ids uuid[]) RETURNS TABLE(id uuid, server_modified_on timestamp with time zone) AS $$
    CLUSTER cluster_for_domain(domain);
    SPLIT case_ids;
    RUN ON hashtext(case_ids::text);
    SELECT id, server_modified_on FROM case_data WHERE case_data.domain = $1 AND case_data.id = ANY($2);
$$ LANGUAGE plproxy;
