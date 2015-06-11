BEGIN;

-- add pgcrypto extension so that we can use the gen_random_uuid function.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS formdata CASCADE;
CREATE TABLE formdata(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain text NOT NULL,
  received_on timestamp without time zone,
  time_start timestamp without time zone,
  time_end timestamp without time zone,
  duration bigint,
  device_id text,
  user_id uuid NOT NULL,
  username text,
  app_id uuid,
  xmlns text NOT NULL,
  form_json text NOT NULL
);

CREATE INDEX formdata_domain on formdata(domain);

DROP TABLE IF EXISTS casedata CASCADE;
CREATE TABLE casedata(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain text NOT NULL,
  version text,
  type text,
  closed boolean DEFAULT FALSE,
  user_id uuid,
  owner_id uuid NOT NULL,
  opened_on timestamp without time zone,
  opened_by uuid,
  closed_on timestamp without time zone,
  closed_by uuid,
  modified_on timestamp without time zone,
  modified_by uuid,
  server_modified_on timestamp without time zone,
  name text,
  external_id text,
  case_json text NOT NULL
);

CREATE INDEX casedata_domain on casedata(domain);
CREATE INDEX casedata_domain_owner on casedata(domain, owner_id);
CREATE INDEX casedata_open_modified_domain on casedata(domain, closed, server_modified_on);

DROP TABLE IF EXISTS caseindex CASCADE;
CREATE TABLE caseindex(
  id bigserial PRIMARY KEY,
  case_id uuid NOT NULL REFERENCES casedata(id),
  identifier text,
  referenced_type text,
  referenced_id uuid NOT NULL REFERENCES casedata(id)
);

DROP TABLE IF EXISTS case_form CASCADE;
CREATE TABLE case_form(
  case_id uuid NOT NULL REFERENCES casedata(id),
  form_id uuid NOT NULL REFERENCES formdata(id)
);

COMMIT;
