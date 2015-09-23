CREATE OR REPLACE FUNCTION update_case(
  case_id text,
  domain text,
  closed boolean,
  owner_id text,
  server_modified_on timestamp,
  version integer,
  case_json jsonb,
  attachments jsonb) AS $$
       UPDATE case_data
       SET close = $3, owner_id = $4:uuid, server_modified_on = $5, version = $6, case_json = $7, attachments = $8)
       WHERE id = $1::uuid
$$ LANGUAGE SQL;
