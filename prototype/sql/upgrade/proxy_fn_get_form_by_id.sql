CREATE OR REPLACE FUNCTION get_form_by_id(domain text, form_id text)
RETURNS SETOF form_data AS $$
    CLUSTER cluster_for_domain(domain);
    RUN ON hashtext(form_id);
    SELECT * FROM form_data WHERE form_data.domain = $1 and form_data.id = $2::uuid;
$$ LANGUAGE plproxy;
