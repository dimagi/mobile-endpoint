CREATE OR REPLACE FUNCTION insert_form(
  domain text,
  form_id text,
  received_on timestamp,
  user_id text,
  md5 text,
  synclog_id text,
  attachments jsonb)
RETURNS integer AS $$
    CLUSTER cluster_for_domain(domain);
    RUN ON hashtext(form_id);
$$ LANGUAGE plproxy;
