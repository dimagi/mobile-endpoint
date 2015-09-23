CREATE OR REPLACE FUNCTION get_reverse_index_case_ids(domain text, case_ids uuid[]) RETURNS SETOF uuid AS $$
    CLUSTER 'hqcluster';
    RUN ON ALL;
    SELECT case_id FROM case_index WHERE case_index.domain = $1 and case_index.referenced_id = ANY($2);
$$ LANGUAGE plproxy;
