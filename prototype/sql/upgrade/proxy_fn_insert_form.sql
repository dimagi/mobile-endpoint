CREATE OR REPLACE FUNCTION insert_form(
  form_id text,
  domain text,
  received_on timestamp,
  user_id text,
  md5 text,
  synclog_id text,
  attachments jsonb)
RETURNS integer AS $$
    CLUSTER 'hqcluster';
    RUN ON hashtext(form_id);
$$ LANGUAGE plproxy;
