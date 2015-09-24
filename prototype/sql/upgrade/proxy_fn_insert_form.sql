CREATE OR REPLACE FUNCTION insert_form(
  domain text,
  form_id text,
  received_on timestamp,
  user_id text,
  md5 text,
  synclog_id text,
  attachments jsonb)
RETURNS integer AS $$
    CLUSTER 'hqcluster';
    RUN ON hashtext(form_id);
$$ LANGUAGE plproxy;
