CREATE OR REPLACE FUNCTION cluster_for_domain(domain text) RETURNS text AS $$
DECLARE
    num_clusters int := 128;
    cluster_name text;
BEGIN
    SELECT 'cluster_' || (hashtext(domain) & (num_clusters - 1)) into cluster_name;
    RETURN cluster_name;
END;
$$ LANGUAGE plpgsql;
