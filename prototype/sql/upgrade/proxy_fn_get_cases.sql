CREATE OR REPLACE FUNCTION get_cases(case_ids text[]) RETURNS SETOF case_data AS $$
    CLUSTER 'hqcluster';
    SPLIT case_ids
    RUN ON hashtext(case_ids);
$$ LANGUAGE plproxy;
