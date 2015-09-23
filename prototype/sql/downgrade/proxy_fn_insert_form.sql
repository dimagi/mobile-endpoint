DROP FUNCTION IF EXISTS insert_form(
  form_id text,
  domain text,
  received_on timestamp,
  user_id text,
  md5 text,
  synclog_id text,
  attachments jsonb);
