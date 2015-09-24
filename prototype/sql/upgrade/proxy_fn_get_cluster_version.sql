CREATE OR REPLACE FUNCTION get_cluster_version ( p_cluster_name text ) RETURNS int
LANGUAGE plpgsql AS $$
DECLARE ret int;
BEGIN
    SELECT version INTO ret FROM cluster where name = p_cluster_name;
    RETURN ret;
END;
$$;
