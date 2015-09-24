CREATE OR REPLACE FUNCTION get_cases(domain text, case_ids uuid[]) RETURNS SETOF case_data AS $$
    CLUSTER cluster_for_domain(domain);
    SPLIT case_ids;
    RUN ON hashtext(case_ids::text);
$$ LANGUAGE plproxy;
