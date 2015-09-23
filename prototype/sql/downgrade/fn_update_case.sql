DROP FUNCTION IF EXISTS update_case(
  case_id text,
  domain text,
  closed boolean,
  owner_id text,
  server_modified_on timestamp,
  version integer,
  case_json jsonb,
  attachments jsonb);
