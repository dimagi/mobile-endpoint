DROP FUNCTION IF EXISTS insert_form(
  domain text,
  form_id text,
  received_on timestamp,
  user_id text,
  md5 text,
  synclog_id text,
  attachments jsonb);
