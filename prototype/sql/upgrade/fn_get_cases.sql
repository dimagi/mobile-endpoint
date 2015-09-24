CREATE OR REPLACE FUNCTION get_cases(domain text, case_ids text[]) RETURNS SETOF case_data AS $$
DECLARE
    row case_data;
BEGIN
    FOR row in SELECT * FROM case_data where case_data.domain = $1 and case_data.id = ANY(case_ids::uuid[]) LOOP
    RETURN NEXT row;
    END LOOP;
    RETURN;
END;
$$ LANGUAGE plpgsql;
