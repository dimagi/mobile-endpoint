CREATE OR REPLACE FUNCTION get_cases(domain text, case_ids text[]) RETURNS SETOF case_data AS $$
BEGIN
    SELECT * FROM case_data where case_data.id = ANY(case_ids);
END;
$$ LANGUAGE plpgsql;
