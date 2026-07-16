\set ON_ERROR_STOP on

REVOKE ALL ON DATABASE :"database_name" FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'database_name', :'app_user') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'database_name', :'audit_user') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_user') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'audit_user') \gexec
SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I',
              :'app_user') \gexec
SELECT format('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO %I',
              :'app_user') \gexec
SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA public TO %I', :'audit_user') \gexec
SELECT format('GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO %I', :'audit_user') \gexec

SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public '
              'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
              :'owner_user', :'app_user') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public '
              'GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %I',
              :'owner_user', :'app_user') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public '
              'GRANT SELECT ON TABLES TO %I', :'owner_user', :'audit_user') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public '
              'GRANT SELECT ON SEQUENCES TO %I', :'owner_user', :'audit_user') \gexec

SELECT format('ALTER ROLE %I SET default_transaction_read_only = off', :'app_user') \gexec
SELECT format('ALTER ROLE %I SET default_transaction_read_only = on', :'audit_user') \gexec
SELECT format('ALTER ROLE %I SET statement_timeout = %L', :'audit_user', '5s') \gexec
SELECT format('ALTER ROLE %I SET lock_timeout = %L', :'audit_user', '1s') \gexec
