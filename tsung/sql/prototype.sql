--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE alembic_version OWNER TO skelly;

--
-- Name: case_data; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE case_data (
    id uuid NOT NULL,
    domain text NOT NULL,
    closed boolean NOT NULL,
    owner_id uuid NOT NULL,
    server_modified_on timestamp without time zone NOT NULL,
    case_json jsonb NOT NULL,
    version integer,
    attachments jsonb
);


ALTER TABLE case_data OWNER TO skelly;

--
-- Name: case_form; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE case_form (
    case_id uuid NOT NULL,
    form_id uuid NOT NULL
);


ALTER TABLE case_form OWNER TO skelly;

--
-- Name: case_index; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE case_index (
    case_id uuid NOT NULL,
    domain text NOT NULL,
    identifier text NOT NULL,
    referenced_id uuid,
    referenced_type text NOT NULL
);


ALTER TABLE case_index OWNER TO skelly;

--
-- Name: form_data; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE form_data (
    id uuid NOT NULL,
    domain text NOT NULL,
    received_on timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    md5 bytea NOT NULL,
    synclog_id uuid,
    attachments jsonb
);


ALTER TABLE form_data OWNER TO skelly;

--
-- Name: form_error; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE form_error (
    id uuid NOT NULL,
    domain text NOT NULL,
    received_on timestamp without time zone NOT NULL,
    user_id uuid NOT NULL,
    md5 bytea NOT NULL,
    type integer NOT NULL,
    duplicate_id uuid,
    attachments jsonb
);


ALTER TABLE form_error OWNER TO skelly;

--
-- Name: ownership_cleanliness_flag; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE ownership_cleanliness_flag (
    domain text NOT NULL,
    owner_id uuid NOT NULL,
    is_clean boolean NOT NULL,
    last_checked timestamp without time zone NOT NULL,
    hint uuid
);


ALTER TABLE ownership_cleanliness_flag OWNER TO skelly;

--
-- Name: synclog; Type: TABLE; Schema: public; Owner: skelly; Tablespace: 
--

CREATE TABLE synclog (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    previous_log_id uuid,
    hash text NOT NULL,
    owner_ids_on_phone uuid[],
    case_ids_on_phone uuid[],
    date timestamp without time zone NOT NULL,
    dependent_case_ids_on_phone uuid[],
    domain text NOT NULL,
    index_tree jsonb
);


ALTER TABLE synclog OWNER TO skelly;

--
-- Name: case_data_pkey; Type: CONSTRAINT; Schema: public; Owner: skelly; Tablespace: 
--

ALTER TABLE ONLY case_data
    ADD CONSTRAINT case_data_pkey PRIMARY KEY (id);


--
-- Name: case_form_pkey; Type: CONSTRAINT; Schema: public; Owner: skelly; Tablespace: 
--

ALTER TABLE ONLY case_form
    ADD CONSTRAINT case_form_pkey PRIMARY KEY (case_id, form_id);


--
-- Name: case_index_pkey; Type: CONSTRAINT; Schema: public; Owner: skelly; Tablespace: 
--

ALTER TABLE ONLY case_index
    ADD CONSTRAINT case_index_pkey PRIMARY KEY (case_id, identifier);


--
-- Name: form_data_pkey; Type: CONSTRAINT; Schema: public; Owner: skelly; Tablespace: 
--

ALTER TABLE ONLY form_data
    ADD CONSTRAINT form_data_pkey PRIMARY KEY (id);


--
-- Name: form_error_pkey; Type: CONSTRAINT; Schema: public; Owner: skelly; Tablespace: 
--

ALTER TABLE ONLY form_error
    ADD CONSTRAINT form_error_pkey PRIMARY KEY (id);


--
-- Name: ownership_cleanliness_flag_pkey; Type: CONSTRAINT; Schema: public; Owner: skelly; Tablespace: 
--

ALTER TABLE ONLY ownership_cleanliness_flag
    ADD CONSTRAINT ownership_cleanliness_flag_pkey PRIMARY KEY (domain, owner_id);


--
-- Name: synclog_pkey; Type: CONSTRAINT; Schema: public; Owner: skelly; Tablespace: 
--

ALTER TABLE ONLY synclog
    ADD CONSTRAINT synclog_pkey PRIMARY KEY (id);


--
-- Name: ix_case_data_domain_closed_modified; Type: INDEX; Schema: public; Owner: skelly; Tablespace: 
--

CREATE INDEX ix_case_data_domain_closed_modified ON case_data USING btree (domain, closed, server_modified_on);


--
-- Name: ix_case_data_domain_owner; Type: INDEX; Schema: public; Owner: skelly; Tablespace: 
--

CREATE INDEX ix_case_data_domain_owner ON case_data USING btree (domain, owner_id);


--
-- Name: ix_case_index_referenced_id; Type: INDEX; Schema: public; Owner: skelly; Tablespace: 
--

CREATE INDEX ix_case_index_referenced_id ON case_index USING btree (domain, referenced_id);


--
-- Name: ix_form_data_domain; Type: INDEX; Schema: public; Owner: skelly; Tablespace: 
--

CREATE INDEX ix_form_data_domain ON form_data USING btree (domain);


--
-- Name: ix_form_error_domain; Type: INDEX; Schema: public; Owner: skelly; Tablespace: 
--

CREATE INDEX ix_form_error_domain ON form_error USING btree (domain);


--
-- Name: case_form_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY case_form
    ADD CONSTRAINT case_form_case_id_fkey FOREIGN KEY (case_id) REFERENCES case_data(id);


--
-- Name: case_form_form_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY case_form
    ADD CONSTRAINT case_form_form_id_fkey FOREIGN KEY (form_id) REFERENCES form_data(id);


--
-- Name: case_index_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY case_index
    ADD CONSTRAINT case_index_case_id_fkey FOREIGN KEY (case_id) REFERENCES case_data(id);


--
-- Name: case_index_referenced_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY case_index
    ADD CONSTRAINT case_index_referenced_id_fkey FOREIGN KEY (referenced_id) REFERENCES case_data(id);


--
-- Name: form_data_synclog_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY form_data
    ADD CONSTRAINT form_data_synclog_id_fkey FOREIGN KEY (synclog_id) REFERENCES synclog(id);


--
-- Name: form_error_duplicate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY form_error
    ADD CONSTRAINT form_error_duplicate_id_fkey FOREIGN KEY (duplicate_id) REFERENCES form_data(id);


--
-- Name: ownership_cleanliness_flag_hint_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY ownership_cleanliness_flag
    ADD CONSTRAINT ownership_cleanliness_flag_hint_fkey FOREIGN KEY (hint) REFERENCES case_data(id);


--
-- Name: synclog_previous_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skelly
--

ALTER TABLE ONLY synclog
    ADD CONSTRAINT synclog_previous_log_id_fkey FOREIGN KEY (previous_log_id) REFERENCES synclog(id);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

