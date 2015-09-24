CREATE OR REPLACE FUNCTION get_cluster_partitions ( p_cluster_name text ) RETURNS SETOF text
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE r record;
BEGIN
    FOR r IN SELECT 'host=' || host || ' port=' || port || ' dbname=' || dbname AS dsn
        FROM logical_partition l JOIN physical_partition p on l.physical_partition = p.name
        WHERE
            p.cluster_name = p_cluster_name
        ORDER BY dbname -- important
    LOOP
        RETURN NEXT r.dsn;
    END LOOP;
    IF NOT found THEN
        RAISE EXCEPTION 'no such cluster : %' , p_cluster_name;
    END IF;
    RETURN;
END;
$$;
