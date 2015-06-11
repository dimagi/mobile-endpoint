BEGIN;

-- add pgcrypto extension so that we can use the gen_random_uuid function.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS formdata CASCADE;
CREATE TABLE formdata(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain text NOT NULL,
  received_on timestamp without time zone,
  user_id uuid NOT NULL,
  form_json text NOT NULL
);

CREATE INDEX formdata_domain on formdata(domain);

DROP TABLE IF EXISTS casedata CASCADE;
CREATE TABLE casedata(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain text NOT NULL,
  closed boolean DEFAULT FALSE,
  owner_id uuid NOT NULL,
  server_modified_on timestamp without time zone,
  case_json text NOT NULL
);

CREATE INDEX casedata_domain on casedata(domain);
CREATE INDEX casedata_domain_owner on casedata(domain, owner_id);
CREATE INDEX casedata_open_modified_domain on casedata(domain, closed, server_modified_on);

DROP TABLE IF EXISTS caseindex CASCADE;
CREATE TABLE caseindex(
  case_id uuid NOT NULL REFERENCES casedata(id),
  referenced_id uuid NOT NULL REFERENCES casedata(id)
);

DROP TABLE IF EXISTS case_form CASCADE;
CREATE TABLE case_form(
  case_id uuid NOT NULL REFERENCES casedata(id),
  form_id uuid NOT NULL REFERENCES formdata(id)
);

COMMIT;
