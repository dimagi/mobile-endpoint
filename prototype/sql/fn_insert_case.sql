CREATE OR REPLACE FUNCTION insert_case(
  case_id text,
  domain text,
  closed boolean,
  owner_id text,
  server_modified_on timestamp,
  version integer,
  case_json jsonb,
  attachments jsonb)
RETURNS integer AS $$
       INSERT INTO case_data (
           id,
           domain,
           closed,
           owner_id,
           server_modified_on,
           version,
           case_json,
           attachments)
       VALUES ($1::uuid, $2, $3, $4::uuid, $5, $6, $7, $8);
       SELECT 1;
$$ LANGUAGE SQL;
