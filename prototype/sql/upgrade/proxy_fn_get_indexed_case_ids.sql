CREATE OR REPLACE FUNCTION get_indexed_case_ids(domain text, case_ids uuid[]) RETURNS SETOF uuid AS $$
    CLUSTER cluster_for_domain(domain);
    SPLIT case_ids;
    RUN ON hashtext(case_ids::text);
    SELECT referenced_id FROM case_index WHERE case_index.domain = $1 and case_index.case_id = ANY($2);
$$ LANGUAGE plproxy;
