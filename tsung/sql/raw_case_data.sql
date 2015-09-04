CREATE TABLE case_data (
    id BIGSERIAL PRIMARY KEY,
    case_id uuid NOT NULL,
    domain text NOT NULL,
    closed boolean NOT NULL,
    owner_id uuid NOT NULL,
    server_modified_on timestamp without time zone NOT NULL,
    case_json json NOT NULL
);

CREATE INDEX ix_case_data_case_id ON case_data USING btree (case_id);

CREATE INDEX ix_case_data_domain_closed_modified ON case_data USING btree (domain, closed, server_modified_on);

CREATE INDEX ix_case_data_domain_owner ON case_data USING btree (domain, owner_id);
