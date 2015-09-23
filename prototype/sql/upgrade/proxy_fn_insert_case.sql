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
    CLUSTER 'hqcluster';
    RUN ON hashtext(case_id);
$$ LANGUAGE plproxy;
