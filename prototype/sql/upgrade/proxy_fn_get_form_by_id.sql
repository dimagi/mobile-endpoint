CREATE OR REPLACE FUNCTION get_form_by_id(domain text, form_id text)
RETURNS SETOF form_data AS $$
    CLUSTER 'hqcluster';
    RUN ON hashtext(form_id);
    SELECT * FROM form_data WHERE id = $1::uuid;
$$ LANGUAGE plproxy;
