--
-- PostgreSQL database dump
--

-- Dumped from database version 10.4
-- Dumped by pg_dump version 11.1

-- Started on 2019-05-03 17:20:21

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 196 (class 1259 OID 19083)
-- Name: OAIPMH_ID_SEQ; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public."OAIPMH_ID_SEQ"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public."OAIPMH_ID_SEQ" OWNER TO postgres;

--
-- TOC entry 197 (class 1259 OID 19085)
-- Name: SAMPLE_ID_SEQ; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public."SAMPLE_ID_SEQ"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public."SAMPLE_ID_SEQ" OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 198 (class 1259 OID 19087)
-- Name: oaipmh; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.oaipmh (
    oaipmh_id bigint DEFAULT nextval('public."OAIPMH_ID_SEQ"'::regclass) NOT NULL,
    oaipmh_key text NOT NULL,
    oaipmh_url text NOT NULL
);


ALTER TABLE public.oaipmh OWNER TO postgres;

--
-- TOC entry 199 (class 1259 OID 19094)
-- Name: sample; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sample (
    sample_id bigint DEFAULT nextval('public."SAMPLE_ID_SEQ"'::regclass) NOT NULL,
    oaipmh_id bigint NOT NULL,
    identifier text NOT NULL,
    datestamp timestamp with time zone,
    alt_identifiers text,
    title text,
    subject text,
    description text,
    "type" text,
    format text,
    coverage text,
    creator text,
    publisher text,
    rights text
);


ALTER TABLE public.sample OWNER TO postgres;

--
-- TOC entry 2681 (class 2606 OID 19102)
-- Name: oaipmh oaipmh_oaipmh_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.oaipmh
    ADD CONSTRAINT oaipmh_oaipmh_key_key UNIQUE (oaipmh_key);


--
-- TOC entry 2683 (class 2606 OID 19104)
-- Name: oaipmh oaipmh_oaipmh_url_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.oaipmh
    ADD CONSTRAINT oaipmh_oaipmh_url_key UNIQUE (oaipmh_url);


--
-- TOC entry 2685 (class 2606 OID 19106)
-- Name: oaipmh oaipmh_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.oaipmh
    ADD CONSTRAINT oaipmh_pkey PRIMARY KEY (oaipmh_id);


--
-- TOC entry 2687 (class 2606 OID 19108)
-- Name: sample sample_identifier_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sample
    ADD CONSTRAINT sample_identifier_key UNIQUE (identifier);


--
-- TOC entry 2689 (class 2606 OID 19110)
-- Name: sample sample_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sample
    ADD CONSTRAINT sample_pkey PRIMARY KEY (sample_id);


--
-- TOC entry 2690 (class 2606 OID 19111)
-- Name: sample sample_oaipmh_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sample
    ADD CONSTRAINT sample_oaipmh_id_fkey FOREIGN KEY (oaipmh_id) REFERENCES public.oaipmh(oaipmh_id);


--
-- TOC entry 2817 (class 0 OID 0)
-- Dependencies: 196
-- Name: SEQUENCE "OAIPMH_ID_SEQ"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public."OAIPMH_ID_SEQ" TO db_users;


--
-- TOC entry 2818 (class 0 OID 0)
-- Dependencies: 197
-- Name: SEQUENCE "SAMPLE_ID_SEQ"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public."SAMPLE_ID_SEQ" TO db_users;


--
-- TOC entry 2819 (class 0 OID 0)
-- Dependencies: 198
-- Name: TABLE oaipmh; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.oaipmh TO db_users;


--
-- TOC entry 2820 (class 0 OID 0)
-- Dependencies: 199
-- Name: TABLE sample; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.sample TO db_users;


-- Completed on 2019-05-03 17:20:22

--
-- PostgreSQL database dump complete
--

