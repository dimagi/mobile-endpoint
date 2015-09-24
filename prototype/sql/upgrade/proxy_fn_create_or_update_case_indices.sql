DROP TYPE IF EXISTS case_index_row;
CREATE TYPE case_index_row AS (identifier text, referenced_id uuid, referenced_type text, is_new boolean);

CREATE OR REPLACE FUNCTION create_or_update_case_indices(domain text, case_id text, indices case_index_row[]) RETURNS integer AS $$
    CLUSTER cluster_for_domain(domain);
    RUN ON hashtext(case_id);
$$ LANGUAGE plproxy;
