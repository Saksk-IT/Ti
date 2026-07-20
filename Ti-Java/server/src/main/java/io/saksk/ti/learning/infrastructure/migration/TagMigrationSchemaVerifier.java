package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.FailureCode;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/** Read-only, fail-closed verification of the externally provisioned operator schema. */
final class TagMigrationSchemaVerifier {

    static final int SCHEMA_VERSION = 1;
    static final String OPERATOR_ROLE = "ti_phase4c_tag_operator";
    static final String SCHEMA_FINGERPRINT =
            "f4361024a36e4e509f1ca4203c2dca5ecfd5bf1eded036e462bbbb20f395f99c";

    private static final List<String> REQUIRED_RELATIONS = List.of(
            "ti_migration.operator_schema_metadata",
            "ti_migration.personal_bank_tag_run",
            "ti_migration.personal_bank_tag_run_source",
            "ti_migration.personal_bank_tag_receipt",
            "ti_migration.personal_bank_tag_audit",
            "public.user_progress",
            "public.user_question_tag_items");
    private static final Set<String> REQUIRED_TRIGGERS = Set.of(
            "personal_bank_tag_run_transition_guard",
            "personal_bank_tag_run_source_insert_guard",
            "personal_bank_tag_run_source_immutable",
            "personal_bank_tag_manifest_complete_from_run",
            "personal_bank_tag_manifest_complete_from_source",
            "personal_bank_tag_receipt_insert_guard",
            "personal_bank_tag_receipt_append_only",
            "personal_bank_tag_receipt_commit_guard",
            "personal_bank_tag_audit_append_only",
            "personal_bank_tag_audit_truncate_guard",
            "personal_bank_tag_target_insert_guard");
    private static final List<String> PRIVILEGES = List.of(
            "SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE",
            "REFERENCES", "TRIGGER");
    private static final List<String> COLUMN_PRIVILEGES = List.of(
            "SELECT", "INSERT", "UPDATE", "REFERENCES");
    private static final Map<String, Set<String>> EXPECTED_PRIVILEGES =
            expectedPrivileges();

    static final String METADATA_SQL = """
            SELECT schema_version, schema_fingerprint
            FROM ti_migration.operator_schema_metadata
            WHERE singleton = TRUE
            """;
    static final String ROLE_SQL = """
            SELECT rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls,
                   rolcanlogin, rolinherit,
                   pg_catalog.has_schema_privilege(
                       current_user, 'ti_migration', 'USAGE'),
                   pg_catalog.has_schema_privilege(
                       current_user, 'ti_migration', 'CREATE'),
                   pg_catalog.has_schema_privilege(
                       current_user, 'public', 'CREATE'),
                   pg_catalog.has_database_privilege(
                       current_user, pg_catalog.current_database(), 'CONNECT'),
                   pg_catalog.has_database_privilege(
                       current_user, pg_catalog.current_database(), 'CREATE'),
                   pg_catalog.has_database_privilege(
                       current_user, pg_catalog.current_database(), 'TEMP'),
                   rolname
            FROM pg_catalog.pg_roles
            WHERE rolname = current_user
            """;
    static final String ROLE_MEMBERSHIP_SQL = """
            SELECT pg_catalog.count(*)
            FROM pg_catalog.pg_auth_members AS membership
            JOIN pg_catalog.pg_roles AS member_role
              ON member_role.oid = membership.member
            WHERE member_role.rolname = current_user
            """;
    static final String RELATION_SQL = """
            SELECT relation_name,
                   pg_catalog.to_regclass(relation_name)::text,
                   pg_catalog.pg_get_userbyid(c.relowner) = current_user
                       AS current_user_owns_relation,
                   c.relkind::text,
                   c.relpersistence::text,
                   c.relrowsecurity,
                   c.relforcerowsecurity
            FROM pg_catalog.unnest(?::text[]) AS requested(relation_name)
            LEFT JOIN pg_catalog.pg_class c
              ON c.oid = pg_catalog.to_regclass(relation_name)
            ORDER BY relation_name
            """;
    static final String TRIGGER_SQL = """
            SELECT t.tgname
            FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE (
                    n.nspname = 'ti_migration'
                    AND c.relname IN (
                        'personal_bank_tag_run',
                        'personal_bank_tag_run_source',
                        'personal_bank_tag_receipt',
                        'personal_bank_tag_audit')
                  OR (
                    n.nspname = 'public'
                    AND c.relname = 'user_question_tag_items'
                    AND t.tgname = 'personal_bank_tag_target_insert_guard'))
              AND NOT t.tgisinternal
              AND t.tgenabled = 'O'
            ORDER BY t.tgname
            """;
    static final String PRIVILEGE_SQL = """
            SELECT pg_catalog.has_table_privilege(current_user, ?, ?)
            """;
    static final String COLUMN_PRIVILEGE_SQL = """
            SELECT attribute.attnum,
                   pg_catalog.has_column_privilege(
                       current_user, relation.oid, attribute.attnum, ?)
            FROM pg_catalog.pg_class AS relation
            JOIN pg_catalog.pg_namespace AS namespace
              ON namespace.oid = relation.relnamespace
            JOIN pg_catalog.pg_attribute AS attribute
              ON attribute.attrelid = relation.oid
             AND attribute.attnum > 0
             AND NOT attribute.attisdropped
            WHERE namespace.nspname = ?
              AND relation.relname = ?
            ORDER BY attribute.attnum
            """;
    static final String SEQUENCE_SQL = """
            SELECT c.relkind::text,
                   c.relpersistence::text,
                   pg_catalog.pg_get_userbyid(c.relowner) = current_user,
                   pg_catalog.has_sequence_privilege(
                       current_user, c.oid, 'SELECT'),
                   pg_catalog.has_sequence_privilege(
                       current_user, c.oid, 'USAGE'),
                   pg_catalog.has_sequence_privilege(
                       current_user, c.oid, 'UPDATE')
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'ti_migration'
              AND c.relname = 'personal_bank_tag_audit_audit_id_seq'
            """;
    static final String ACL_CLOSURE_SQL = """
            WITH allowed_schemas(schema_name, privilege_name) AS (
                VALUES
                    ('public', 'USAGE'),
                    ('ti_migration', 'USAGE')
            ),
            schema_grants AS (
                SELECT namespace.nspname AS object_name,
                       privilege.privilege_name
                FROM pg_catalog.pg_namespace AS namespace
                CROSS JOIN (VALUES ('USAGE'), ('CREATE'))
                    AS privilege(privilege_name)
                WHERE namespace.nspname NOT IN (
                        'information_schema', 'pg_catalog')
                  AND namespace.nspname NOT LIKE 'pg_toast%'
                  AND namespace.nspname NOT LIKE 'pg_temp_%'
                  AND pg_catalog.has_schema_privilege(
                      current_user, namespace.oid, privilege.privilege_name)
            ),
            allowed_relations(object_name, privilege_name) AS (
                VALUES
                    ('public.user_progress', 'SELECT'),
                    ('public.user_question_tag_items', 'SELECT'),
                    ('public.user_question_tag_items', 'INSERT'),
                    ('ti_migration.operator_schema_metadata', 'SELECT'),
                    ('ti_migration.personal_bank_tag_run', 'SELECT'),
                    ('ti_migration.personal_bank_tag_run', 'INSERT'),
                    ('ti_migration.personal_bank_tag_run', 'UPDATE'),
                    ('ti_migration.personal_bank_tag_run_source', 'SELECT'),
                    ('ti_migration.personal_bank_tag_run_source', 'INSERT'),
                    ('ti_migration.personal_bank_tag_receipt', 'SELECT'),
                    ('ti_migration.personal_bank_tag_receipt', 'INSERT')
            ),
            relation_grants AS (
                SELECT namespace.nspname || '.' || relation.relname
                           AS object_name,
                       privilege.privilege_name
                FROM pg_catalog.pg_class AS relation
                JOIN pg_catalog.pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                CROSS JOIN (VALUES
                    ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'),
                    ('TRUNCATE'), ('REFERENCES'), ('TRIGGER'))
                    AS privilege(privilege_name)
                WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f')
                  AND namespace.nspname NOT IN (
                        'information_schema', 'pg_catalog')
                  AND namespace.nspname NOT LIKE 'pg_toast%'
                  AND namespace.nspname NOT LIKE 'pg_temp_%'
                  AND pg_catalog.has_table_privilege(
                      current_user, relation.oid, privilege.privilege_name)
            ),
            column_grants AS (
                SELECT namespace.nspname || '.' || relation.relname
                           || '.' || attribute.attname AS object_name,
                       acl.privilege_type
                FROM pg_catalog.pg_class AS relation
                JOIN pg_catalog.pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                JOIN pg_catalog.pg_attribute AS attribute
                  ON attribute.attrelid = relation.oid
                 AND attribute.attnum > 0
                 AND NOT attribute.attisdropped
                CROSS JOIN LATERAL pg_catalog.aclexplode(attribute.attacl)
                    AS acl
                WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f')
                  AND namespace.nspname NOT IN (
                        'information_schema', 'pg_catalog')
                  AND namespace.nspname NOT LIKE 'pg_toast%'
                  AND namespace.nspname NOT LIKE 'pg_temp_%'
                  AND (
                      acl.grantee = 0
                      OR acl.grantee = (
                          SELECT role_value.oid
                          FROM pg_catalog.pg_roles AS role_value
                          WHERE role_value.rolname = current_user))
            ),
            sequence_grants AS (
                SELECT namespace.nspname || '.' || relation.relname
                           AS object_name,
                       privilege.privilege_name
                FROM pg_catalog.pg_class AS relation
                JOIN pg_catalog.pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                CROSS JOIN (VALUES ('SELECT'), ('USAGE'), ('UPDATE'))
                    AS privilege(privilege_name)
                WHERE relation.relkind = 'S'
                  AND namespace.nspname NOT IN (
                        'information_schema', 'pg_catalog')
                  AND namespace.nspname NOT LIKE 'pg_toast%'
                  AND namespace.nspname NOT LIKE 'pg_temp_%'
                  AND pg_catalog.has_sequence_privilege(
                      current_user, relation.oid, privilege.privilege_name)
            ),
            function_grants AS (
                SELECT namespace.nspname || '.' || function_value.proname
                           AS object_name,
                       'EXECUTE'::text AS privilege_name
                FROM pg_catalog.pg_proc AS function_value
                JOIN pg_catalog.pg_namespace AS namespace
                  ON namespace.oid = function_value.pronamespace
                WHERE namespace.nspname NOT IN (
                        'information_schema', 'pg_catalog')
                  AND namespace.nspname NOT LIKE 'pg_toast%'
                  AND namespace.nspname NOT LIKE 'pg_temp_%'
                  AND pg_catalog.has_function_privilege(
                      current_user, function_value.oid, 'EXECUTE')
            )
            SELECT object_kind, object_name, privilege_name
            FROM (
                SELECT 'SCHEMA'::text AS object_kind,
                       grant_value.object_name,
                       grant_value.privilege_name
                FROM schema_grants AS grant_value
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM allowed_schemas AS allowed
                    WHERE allowed.schema_name = grant_value.object_name
                      AND allowed.privilege_name = grant_value.privilege_name)

                UNION ALL

                SELECT 'RELATION', grant_value.object_name,
                       grant_value.privilege_name
                FROM relation_grants AS grant_value
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM allowed_relations AS allowed
                    WHERE allowed.object_name = grant_value.object_name
                      AND allowed.privilege_name = grant_value.privilege_name)

                UNION ALL

                SELECT 'COLUMN', object_name, privilege_type
                FROM column_grants

                UNION ALL

                SELECT 'SEQUENCE', object_name, privilege_name
                FROM sequence_grants

                UNION ALL

                SELECT 'FUNCTION', object_name, privilege_name
                FROM function_grants
            ) AS unexpected_grant
            ORDER BY object_kind, object_name, privilege_name
            """;
    static final String CATALOG_SQL = """
            WITH canonical_context AS MATERIALIZED (
                SELECT pg_catalog.set_config(
                    'search_path', 'pg_catalog, public', true) AS search_path
            ),
            schemas AS MATERIALIZED (
                SELECT namespace.oid,
                       namespace.nspname,
                       namespace.nspowner,
                       namespace.nspacl,
                       pg_catalog.pg_get_userbyid(namespace.nspowner)
                           AS owner_name,
                       owner.rolsuper,
                       owner.rolcreaterole,
                       owner.rolcreatedb,
                       owner.rolcanlogin,
                       owner.rolinherit,
                       owner.rolreplication,
                       owner.rolbypassrls
                FROM pg_catalog.pg_namespace AS namespace
                JOIN pg_catalog.pg_roles AS owner
                  ON owner.oid = namespace.nspowner
                CROSS JOIN canonical_context
                WHERE namespace.nspname IN ('public', 'ti_migration')
            ),
            relations AS MATERIALIZED (
                SELECT relation.oid,
                       namespace.nspname,
                       relation.relname,
                       relation.relkind,
                       relation.relpersistence,
                       relation.relrowsecurity,
                       relation.relforcerowsecurity,
                       relation.relreplident,
                       relation.relispartition,
                       relation.relowner,
                       relation.relacl,
                       relation.reloptions,
                       pg_catalog.pg_get_userbyid(relation.relowner)
                           AS owner_name,
                       owner.rolsuper,
                       owner.rolcreaterole,
                       owner.rolcreatedb,
                       owner.rolcanlogin,
                       owner.rolinherit,
                       owner.rolreplication,
                       owner.rolbypassrls,
                       COALESCE(access_method.amname, '<NONE>') AS access_method,
                       COALESCE(tablespace.spcname, '<DEFAULT>') AS tablespace
                FROM pg_catalog.pg_class AS relation
                JOIN pg_catalog.pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                JOIN pg_catalog.pg_roles AS owner
                  ON owner.oid = relation.relowner
                LEFT JOIN pg_catalog.pg_am AS access_method
                  ON access_method.oid = relation.relam
                LEFT JOIN pg_catalog.pg_tablespace AS tablespace
                  ON tablespace.oid = relation.reltablespace
                CROSS JOIN canonical_context
                WHERE namespace.nspname = 'ti_migration'
                   OR (namespace.nspname, relation.relname) IN (
                       ('public', 'user_progress'),
                       ('public', 'user_question_tag_items'))
            ),
            functions AS MATERIALIZED (
                SELECT function_value.*,
                       function_namespace.nspname,
                       language_value.lanname,
                       pg_catalog.pg_get_userbyid(function_value.proowner)
                           AS owner_name,
                       owner.rolsuper,
                       owner.rolcreaterole,
                       owner.rolcreatedb,
                       owner.rolcanlogin,
                       owner.rolinherit,
                       owner.rolreplication,
                       owner.rolbypassrls
                FROM pg_catalog.pg_proc AS function_value
                JOIN pg_catalog.pg_namespace AS function_namespace
                  ON function_namespace.oid = function_value.pronamespace
                JOIN pg_catalog.pg_language AS language_value
                  ON language_value.oid = function_value.prolang
                JOIN pg_catalog.pg_roles AS owner
                  ON owner.oid = function_value.proowner
                CROSS JOIN canonical_context
                WHERE function_namespace.nspname = 'ti_migration'
            ),
            facts AS (
                SELECT pg_catalog.jsonb_build_array(
                           'SCHEMA', schema_value.nspname,
                           schema_value.owner_name,
                           schema_value.rolsuper,
                           schema_value.rolcreaterole,
                           schema_value.rolcreatedb,
                           schema_value.rolcanlogin,
                           schema_value.rolinherit,
                           schema_value.rolreplication,
                           schema_value.rolbypassrls)::text AS fact
                FROM schemas AS schema_value

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'SCHEMA_ACL', schema_value.nspname,
                           pg_catalog.pg_get_userbyid(acl.grantor),
                           CASE WHEN acl.grantee = 0 THEN 'PUBLIC'
                                ELSE pg_catalog.pg_get_userbyid(acl.grantee) END,
                           acl.privilege_type,
                           acl.is_grantable)::text
                FROM schemas AS schema_value
                CROSS JOIN LATERAL pg_catalog.aclexplode(
                    COALESCE(
                        schema_value.nspacl,
                        pg_catalog.acldefault(
                            'n', schema_value.nspowner))) AS acl

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'RELATION', relation.nspname, relation.relname,
                           relation.relkind::text,
                           relation.relpersistence::text,
                           relation.relrowsecurity,
                           relation.relforcerowsecurity,
                           relation.relreplident::text,
                           relation.relispartition,
                           relation.access_method,
                           relation.tablespace,
                           COALESCE(relation.reloptions::text, '<NULL>'),
                           relation.owner_name,
                           relation.rolsuper,
                           relation.rolcreaterole,
                           relation.rolcreatedb,
                           relation.rolcanlogin,
                           relation.rolinherit,
                           relation.rolreplication,
                           relation.rolbypassrls)::text
                FROM relations AS relation

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'RELATION_ACL', relation.nspname, relation.relname,
                           pg_catalog.pg_get_userbyid(acl.grantor),
                           CASE WHEN acl.grantee = 0 THEN 'PUBLIC'
                                ELSE pg_catalog.pg_get_userbyid(acl.grantee) END,
                           acl.privilege_type,
                           acl.is_grantable)::text
                FROM relations AS relation
                CROSS JOIN LATERAL pg_catalog.aclexplode(
                    COALESCE(
                        relation.relacl,
                        CASE WHEN relation.relkind = 'S'
                             THEN pg_catalog.acldefault('s', relation.relowner)
                             ELSE pg_catalog.acldefault('r', relation.relowner)
                        END)) AS acl
                WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
                  AND (acl.privilege_type <> 'MAINTAIN'
                       OR acl.grantee <> relation.relowner)

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'COLUMN', relation.nspname, relation.relname,
                           attribute.attnum,
                           attribute.attname,
                           COALESCE(type_namespace.nspname, '<NONE>'),
                           COALESCE(type_value.typname, '<NONE>'),
                           pg_catalog.format_type(
                               attribute.atttypid, attribute.atttypmod),
                           attribute.atttypmod,
                           attribute.attlen,
                           attribute.attndims,
                           attribute.attnotnull,
                           attribute.atthasdef,
                           attribute.attidentity::text,
                           attribute.attgenerated::text,
                           attribute.attisdropped,
                           attribute.attislocal,
                           attribute.attinhcount,
                           COALESCE(attribute.attstattarget, -1),
                           attribute.atthasmissing,
                           COALESCE(attribute.attmissingval::text, '<NULL>'),
                           CASE WHEN attribute.attcollation = 0 THEN '<NONE>'
                                ELSE pg_catalog.concat_ws(
                                    '.', collation_namespace.nspname,
                                    collation_value.collname) END,
                           attribute.attstorage::text,
                           attribute.attcompression::text,
                           COALESCE(attribute.attoptions::text, '<NULL>'),
                           COALESCE(pg_catalog.pg_get_expr(
                               default_value.adbin,
                               default_value.adrelid,
                               false), '<NULL>'))::text
                FROM relations AS relation
                JOIN pg_catalog.pg_attribute AS attribute
                  ON attribute.attrelid = relation.oid
                 AND attribute.attnum > 0
                LEFT JOIN pg_catalog.pg_type AS type_value
                  ON type_value.oid = attribute.atttypid
                LEFT JOIN pg_catalog.pg_namespace AS type_namespace
                  ON type_namespace.oid = type_value.typnamespace
                LEFT JOIN pg_catalog.pg_attrdef AS default_value
                  ON default_value.adrelid = attribute.attrelid
                 AND default_value.adnum = attribute.attnum
                LEFT JOIN pg_catalog.pg_collation AS collation_value
                  ON collation_value.oid = attribute.attcollation
                LEFT JOIN pg_catalog.pg_namespace AS collation_namespace
                  ON collation_namespace.oid = collation_value.collnamespace
                WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f')

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'COLUMN_ACL', relation.nspname, relation.relname,
                           attribute.attnum,
                           pg_catalog.pg_get_userbyid(acl.grantor),
                           CASE WHEN acl.grantee = 0 THEN 'PUBLIC'
                                ELSE pg_catalog.pg_get_userbyid(acl.grantee) END,
                           acl.privilege_type,
                           acl.is_grantable)::text
                FROM relations AS relation
                JOIN pg_catalog.pg_attribute AS attribute
                  ON attribute.attrelid = relation.oid
                 AND attribute.attnum > 0
                CROSS JOIN LATERAL pg_catalog.aclexplode(
                    COALESCE(
                        attribute.attacl,
                        pg_catalog.acldefault(
                            'c', relation.relowner))) AS acl
                WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f')

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'CONSTRAINT', relation.nspname, relation.relname,
                           constraint_value.conname,
                           constraint_value.contype::text,
                           constraint_value.condeferrable,
                           constraint_value.condeferred,
                           constraint_value.convalidated,
                           constraint_value.confmatchtype::text,
                           constraint_value.confupdtype::text,
                           constraint_value.confdeltype::text,
                           constraint_value.conislocal,
                           constraint_value.coninhcount,
                           constraint_value.connoinherit,
                           COALESCE(referenced_namespace.nspname, '<NONE>'),
                           COALESCE(referenced_relation.relname, '<NONE>'),
                           COALESCE(constraint_value.conkey::text, '<NULL>'),
                           COALESCE(constraint_value.confkey::text, '<NULL>'),
                           pg_catalog.pg_get_constraintdef(
                               constraint_value.oid, false))::text
                FROM relations AS relation
                JOIN pg_catalog.pg_constraint AS constraint_value
                  ON constraint_value.conrelid = relation.oid
                 /* PostgreSQL 18 additionally materializes NOT NULL here. */
                 AND constraint_value.contype <> 'n'
                LEFT JOIN pg_catalog.pg_class AS referenced_relation
                  ON referenced_relation.oid = constraint_value.confrelid
                LEFT JOIN pg_catalog.pg_namespace AS referenced_namespace
                  ON referenced_namespace.oid =
                     referenced_relation.relnamespace

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'INDEX', relation.nspname, relation.relname,
                           index_namespace.nspname,
                           index_relation.relname,
                           pg_catalog.pg_get_userbyid(index_relation.relowner),
                           access_method.amname,
                           COALESCE(tablespace.spcname, '<DEFAULT>'),
                           index_relation.relpersistence::text,
                           COALESCE(index_relation.reloptions::text, '<NULL>'),
                           index_value.indisunique,
                           index_value.indnullsnotdistinct,
                           index_value.indisprimary,
                           index_value.indisexclusion,
                           index_value.indimmediate,
                           index_value.indisclustered,
                           index_value.indisvalid,
                           index_value.indcheckxmin,
                           index_value.indisready,
                           index_value.indislive,
                           index_value.indisreplident,
                           index_value.indnatts,
                           index_value.indnkeyatts,
                           index_value.indkey::text,
                           index_value.indoption::text,
                           COALESCE((
                               SELECT pg_catalog.jsonb_agg(
                                   pg_catalog.jsonb_build_array(
                                       position_value,
                                       CASE
                                           WHEN index_value.indcollation[
                                                   position_value] = 0
                                           THEN '<NONE>'
                                           ELSE pg_catalog.concat_ws(
                                               '.', key_collation_namespace.nspname,
                                               key_collation.collname)
                                       END,
                                       COALESCE(opclass_namespace.nspname, '<NONE>'),
                                       COALESCE(opclass_value.opcname, '<NONE>'),
                                       index_value.indoption[
                                           position_value]::text)
                                   ORDER BY position_value)
                               FROM pg_catalog.generate_series(
                                   0, index_value.indnatts - 1)
                                   AS position(position_value)
                               LEFT JOIN pg_catalog.pg_collation AS key_collation
                                 ON key_collation.oid =
                                    index_value.indcollation[position_value]
                               LEFT JOIN pg_catalog.pg_namespace
                                   AS key_collation_namespace
                                 ON key_collation_namespace.oid =
                                    key_collation.collnamespace
                               LEFT JOIN pg_catalog.pg_opclass AS opclass_value
                                 ON opclass_value.oid =
                                    index_value.indclass[position_value]
                               LEFT JOIN pg_catalog.pg_namespace
                                   AS opclass_namespace
                                 ON opclass_namespace.oid =
                                    opclass_value.opcnamespace
                           ), '[]'::jsonb),
                           COALESCE(pg_catalog.pg_get_expr(
                               index_value.indexprs,
                               index_value.indrelid,
                               false), '<NULL>'),
                           COALESCE(pg_catalog.pg_get_expr(
                               index_value.indpred,
                               index_value.indrelid,
                               false), '<NULL>'),
                           pg_catalog.pg_get_indexdef(
                               index_value.indexrelid, 0, false))::text
                FROM relations AS relation
                JOIN pg_catalog.pg_index AS index_value
                  ON index_value.indrelid = relation.oid
                JOIN pg_catalog.pg_class AS index_relation
                  ON index_relation.oid = index_value.indexrelid
                JOIN pg_catalog.pg_namespace AS index_namespace
                  ON index_namespace.oid = index_relation.relnamespace
                JOIN pg_catalog.pg_am AS access_method
                  ON access_method.oid = index_relation.relam
                LEFT JOIN pg_catalog.pg_tablespace AS tablespace
                  ON tablespace.oid = index_relation.reltablespace

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'TRIGGER', relation.nspname, relation.relname,
                           trigger_value.tgname,
                           trigger_value.tgtype,
                           trigger_value.tgenabled::text,
                           trigger_value.tgdeferrable,
                           trigger_value.tginitdeferred,
                           trigger_value.tgnargs,
                           pg_catalog.encode(trigger_value.tgargs, 'hex'),
                           COALESCE(trigger_constraint.conname, '<NONE>'),
                           COALESCE(constraint_namespace.nspname, '<NONE>'),
                           COALESCE(constraint_relation.relname, '<NONE>'),
                           function_namespace.nspname,
                           function_value.proname,
                           pg_catalog.pg_get_function_identity_arguments(
                               function_value.oid),
                           pg_catalog.pg_get_userbyid(function_value.proowner),
                           function_value.prosecdef,
                           function_value.provolatile::text,
                           function_value.proparallel::text,
                           COALESCE(function_value.proconfig::text, '<NULL>'),
                           pg_catalog.has_function_privilege(
                               current_user, function_value.oid, 'EXECUTE'),
                           COALESCE(pg_catalog.pg_get_expr(
                               trigger_value.tgqual,
                               trigger_value.tgrelid,
                               false), '<NULL>'),
                           pg_catalog.pg_get_triggerdef(
                               trigger_value.oid, false))::text
                FROM relations AS relation
                JOIN pg_catalog.pg_trigger AS trigger_value
                  ON trigger_value.tgrelid = relation.oid
                 AND NOT trigger_value.tgisinternal
                JOIN pg_catalog.pg_proc AS function_value
                  ON function_value.oid = trigger_value.tgfoid
                JOIN pg_catalog.pg_namespace AS function_namespace
                  ON function_namespace.oid = function_value.pronamespace
                LEFT JOIN pg_catalog.pg_constraint AS trigger_constraint
                  ON trigger_constraint.oid = trigger_value.tgconstraint
                LEFT JOIN pg_catalog.pg_class AS constraint_relation
                  ON constraint_relation.oid = trigger_value.tgconstrrelid
                LEFT JOIN pg_catalog.pg_namespace AS constraint_namespace
                  ON constraint_namespace.oid =
                     constraint_relation.relnamespace

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'FUNCTION', function_value.nspname,
                           function_value.proname,
                           pg_catalog.pg_get_function_identity_arguments(
                               function_value.oid),
                           pg_catalog.pg_get_function_arguments(
                               function_value.oid),
                           pg_catalog.pg_get_function_result(
                               function_value.oid),
                           function_value.lanname,
                           function_value.prokind::text,
                           function_value.proisstrict,
                           function_value.proretset,
                           function_value.pronargs,
                           function_value.pronargdefaults,
                           function_value.provolatile::text,
                           function_value.proparallel::text,
                           function_value.prosecdef,
                           function_value.proleakproof,
                           COALESCE(function_value.proconfig::text, '<NULL>'),
                           COALESCE(function_value.probin, '<NULL>'),
                           function_value.owner_name,
                           function_value.rolsuper,
                           function_value.rolcreaterole,
                           function_value.rolcreatedb,
                           function_value.rolcanlogin,
                           function_value.rolinherit,
                           function_value.rolreplication,
                           function_value.rolbypassrls,
                           pg_catalog.has_function_privilege(
                               current_user, function_value.oid, 'EXECUTE'),
                           function_value.prosrc)::text
                FROM functions AS function_value

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'FUNCTION_ACL', function_value.nspname,
                           function_value.proname,
                           pg_catalog.pg_get_function_identity_arguments(
                               function_value.oid),
                           pg_catalog.pg_get_userbyid(acl.grantor),
                           CASE WHEN acl.grantee = 0 THEN 'PUBLIC'
                                ELSE pg_catalog.pg_get_userbyid(acl.grantee) END,
                           acl.privilege_type,
                           acl.is_grantable)::text
                FROM functions AS function_value
                CROSS JOIN LATERAL pg_catalog.aclexplode(
                    COALESCE(
                        function_value.proacl,
                        pg_catalog.acldefault(
                            'f', function_value.proowner))) AS acl

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'SEQUENCE', relation.nspname, relation.relname,
                           pg_catalog.format_type(
                               sequence_value.seqtypid, NULL),
                           sequence_value.seqstart,
                           sequence_value.seqincrement,
                           sequence_value.seqmax,
                           sequence_value.seqmin,
                           sequence_value.seqcache,
                           sequence_value.seqcycle)::text
                FROM relations AS relation
                JOIN pg_catalog.pg_sequence AS sequence_value
                  ON sequence_value.seqrelid = relation.oid
                WHERE relation.relkind = 'S'

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'SEQUENCE_DEPENDENCY',
                           sequence_relation.nspname,
                           sequence_relation.relname,
                           dependency.deptype::text,
                           referenced_namespace.nspname,
                           referenced_relation.relname,
                           referenced_attribute.attname)::text
                FROM relations AS sequence_relation
                JOIN pg_catalog.pg_depend AS dependency
                  ON dependency.classid =
                     pg_catalog.to_regclass('pg_catalog.pg_class')
                 AND dependency.objid = sequence_relation.oid
                 AND dependency.refclassid =
                     pg_catalog.to_regclass('pg_catalog.pg_class')
                 AND dependency.deptype IN ('a', 'i')
                JOIN pg_catalog.pg_class AS referenced_relation
                  ON referenced_relation.oid = dependency.refobjid
                JOIN pg_catalog.pg_namespace AS referenced_namespace
                  ON referenced_namespace.oid =
                     referenced_relation.relnamespace
                JOIN pg_catalog.pg_attribute AS referenced_attribute
                  ON referenced_attribute.attrelid = dependency.refobjid
                 AND referenced_attribute.attnum = dependency.refobjsubid
                WHERE sequence_relation.relkind = 'S'

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'RULE', relation.nspname, relation.relname,
                           rule_value.rulename,
                           rule_value.ev_type::text,
                           rule_value.ev_enabled::text,
                           rule_value.is_instead,
                           pg_catalog.pg_get_ruledef(
                               rule_value.oid, false))::text
                FROM relations AS relation
                JOIN pg_catalog.pg_rewrite AS rule_value
                  ON rule_value.ev_class = relation.oid
                 AND rule_value.rulename <> '_RETURN'

                UNION ALL
                SELECT pg_catalog.jsonb_build_array(
                           'POLICY', relation.nspname, relation.relname,
                           policy_value.polname,
                           policy_value.polcmd::text,
                           policy_value.polpermissive,
                           COALESCE((
                               SELECT pg_catalog.jsonb_agg(
                                   CASE WHEN role_oid = 0 THEN 'PUBLIC'
                                        ELSE pg_catalog.pg_get_userbyid(
                                            role_oid) END
                                   ORDER BY CASE WHEN role_oid = 0 THEN 'PUBLIC'
                                        ELSE pg_catalog.pg_get_userbyid(
                                            role_oid) END)
                               FROM pg_catalog.unnest(policy_value.polroles)
                                   AS policy_role(role_oid)
                           ), '[]'::jsonb),
                           COALESCE(pg_catalog.pg_get_expr(
                               policy_value.polqual,
                               policy_value.polrelid,
                               false), '<NULL>'),
                           COALESCE(pg_catalog.pg_get_expr(
                               policy_value.polwithcheck,
                               policy_value.polrelid,
                               false), '<NULL>'))::text
                FROM relations AS relation
                JOIN pg_catalog.pg_policy AS policy_value
                  ON policy_value.polrelid = relation.oid
            )
            SELECT fact
            FROM facts
            ORDER BY fact COLLATE "C"
            """;

    void verify(Connection connection) throws SchemaVerificationException {
        Objects.requireNonNull(connection, "connection");
        try {
            verifyMetadata(connection);
            verifyRole(connection);
            verifyRoleMembership(connection);
            verifyRelations(connection);
            verifyTriggers(connection);
            verifyPrivileges(connection);
            verifySequence(connection);
            verifyAclClosure(connection);
            verifyCatalog(connection);
        } catch (SchemaVerificationException failure) {
            throw failure;
        } catch (SQLException failure) {
            FailureCode code = switch (failure.getSQLState()) {
                case "42501" -> FailureCode.SCHEMA_ACL_MISMATCH;
                case "3F000", "42704", "42P01" -> FailureCode.SCHEMA_MISSING;
                case null, default -> FailureCode.SQL_FAILURE;
            };
            throw new SchemaVerificationException(code, failure);
        }
    }

    static List<String> statementSurface() {
        return List.of(
                METADATA_SQL, ROLE_SQL, ROLE_MEMBERSHIP_SQL, RELATION_SQL,
                TRIGGER_SQL, PRIVILEGE_SQL, COLUMN_PRIVILEGE_SQL,
                SEQUENCE_SQL, ACL_CLOSURE_SQL, CATALOG_SQL);
    }

    private static void verifyMetadata(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement = connection.prepareStatement(METADATA_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next() || row.getInt(1) != SCHEMA_VERSION
                    || !SCHEMA_FINGERPRINT.equals(row.getString(2))
                    || row.next()) {
                throw new SchemaVerificationException(
                        FailureCode.SCHEMA_FINGERPRINT_MISMATCH);
            }
        }
    }

    private static void verifyRole(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement = connection.prepareStatement(ROLE_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()
                    || row.getBoolean(1)
                    || row.getBoolean(2)
                    || row.getBoolean(3)
                    || row.getBoolean(4)
                    || row.getBoolean(5)
                    || row.getBoolean(6)
                    || row.getBoolean(7)
                    || !row.getBoolean(8)
                    || row.getBoolean(9)
                    || row.getBoolean(10)
                    || row.getBoolean(11)
                    || row.getBoolean(12)
                    || row.getBoolean(13)
                    || !OPERATOR_ROLE.equals(row.getString(14))
                    || row.next()) {
                throw new SchemaVerificationException(
                        FailureCode.SCHEMA_ACL_MISMATCH);
            }
        }
    }

    private static void verifyRoleMembership(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement =
                     connection.prepareStatement(ROLE_MEMBERSHIP_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next() || row.getLong(1) != 0L || row.next()) {
                throw new SchemaVerificationException(
                        FailureCode.SCHEMA_ACL_MISMATCH);
            }
        }
    }

    private static void verifyColumnPrivileges(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement =
                     connection.prepareStatement(COLUMN_PRIVILEGE_SQL)) {
            for (Map.Entry<String, Set<String>> relation
                    : EXPECTED_PRIVILEGES.entrySet()) {
                int separator = relation.getKey().indexOf('.');
                String namespace = relation.getKey().substring(0, separator);
                String relationName = relation.getKey().substring(separator + 1);
                for (String privilege : COLUMN_PRIVILEGES) {
                    statement.setString(1, privilege);
                    statement.setString(2, namespace);
                    statement.setString(3, relationName);
                    try (ResultSet row = statement.executeQuery()) {
                        int columns = 0;
                        while (row.next()) {
                            columns++;
                            if (row.getBoolean(2)
                                    != relation.getValue().contains(privilege)) {
                                throw new SchemaVerificationException(
                                        FailureCode.SCHEMA_ACL_MISMATCH);
                            }
                        }
                        if (columns == 0) {
                            throw new SchemaVerificationException(
                                    FailureCode.SCHEMA_MISSING);
                        }
                    }
                }
            }
        }
    }

    private static void verifyRelations(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement = connection.prepareStatement(RELATION_SQL)) {
            statement.setArray(1, connection.createArrayOf(
                    "text", REQUIRED_RELATIONS.toArray(String[]::new)));
            try (ResultSet row = statement.executeQuery()) {
                int count = 0;
                while (row.next()) {
                    count++;
                    if (row.getString(2) == null
                            || row.getBoolean(3)
                            || !"r".equals(row.getString(4))
                            || !"p".equals(row.getString(5))
                            || row.getBoolean(6)
                            || row.getBoolean(7)) {
                        throw new SchemaVerificationException(
                                row.getString(2) == null
                                        ? FailureCode.SCHEMA_MISSING
                                        : FailureCode.SCHEMA_ACL_MISMATCH);
                    }
                }
                if (count != REQUIRED_RELATIONS.size()) {
                    throw new SchemaVerificationException(FailureCode.SCHEMA_MISSING);
                }
            }
        }
    }

    private static void verifyTriggers(Connection connection)
            throws SQLException, SchemaVerificationException {
        java.util.HashSet<String> actual = new java.util.HashSet<>();
        try (PreparedStatement statement = connection.prepareStatement(TRIGGER_SQL);
             ResultSet row = statement.executeQuery()) {
            while (row.next()) {
                actual.add(row.getString(1));
            }
        }
        if (!actual.equals(REQUIRED_TRIGGERS)) {
            throw new SchemaVerificationException(
                    FailureCode.SCHEMA_FINGERPRINT_MISMATCH);
        }
    }

    private static void verifyPrivileges(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement = connection.prepareStatement(PRIVILEGE_SQL)) {
            for (Map.Entry<String, Set<String>> relation
                    : EXPECTED_PRIVILEGES.entrySet()) {
                for (String privilege : PRIVILEGES) {
                    statement.setString(1, relation.getKey());
                    statement.setString(2, privilege);
                    try (ResultSet row = statement.executeQuery()) {
                        boolean actual = row.next() && row.getBoolean(1) && !row.next();
                        if (actual != relation.getValue().contains(privilege)) {
                            throw new SchemaVerificationException(
                                    FailureCode.SCHEMA_ACL_MISMATCH);
                        }
                    }
                }
            }
        }
        verifyColumnPrivileges(connection);
    }

    private static void verifySequence(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement = connection.prepareStatement(SEQUENCE_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()
                    || !"S".equals(row.getString(1))
                    || !"p".equals(row.getString(2))
                    || row.getBoolean(3)
                    || row.getBoolean(4)
                    || row.getBoolean(5)
                    || row.getBoolean(6)
                    || row.next()) {
                throw new SchemaVerificationException(
                        FailureCode.SCHEMA_ACL_MISMATCH);
            }
        }
    }

    private static void verifyAclClosure(Connection connection)
            throws SQLException, SchemaVerificationException {
        try (PreparedStatement statement =
                     connection.prepareStatement(ACL_CLOSURE_SQL);
             ResultSet row = statement.executeQuery()) {
            if (row.next()) {
                throw new SchemaVerificationException(
                        FailureCode.SCHEMA_ACL_MISMATCH);
            }
        }
    }

    private static void verifyCatalog(Connection connection)
            throws SQLException, SchemaVerificationException {
        String actual = catalogFingerprint(connection);
        if (!SCHEMA_FINGERPRINT.equals(actual)) {
            throw new SchemaVerificationException(
                    FailureCode.SCHEMA_FINGERPRINT_MISMATCH);
        }
    }

    static String catalogFingerprint(Connection connection) throws SQLException {
        return TagMigrationDigests.sha256Utf8(
                String.join("\n", catalogFacts(connection)));
    }

    static List<String> catalogFacts(Connection connection) throws SQLException {
        List<String> facts = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(CATALOG_SQL);
             ResultSet row = statement.executeQuery()) {
            while (row.next()) {
                facts.add(row.getString(1));
            }
        }
        if (facts.isEmpty()) {
            throw new SQLException("operator catalog facts are empty");
        }
        return List.copyOf(facts);
    }

    private static Map<String, Set<String>> expectedPrivileges() {
        Map<String, Set<String>> privileges = new LinkedHashMap<>();
        privileges.put(
                "ti_migration.operator_schema_metadata", Set.of("SELECT"));
        privileges.put(
                "ti_migration.personal_bank_tag_run",
                Set.of("SELECT", "INSERT", "UPDATE"));
        privileges.put(
                "ti_migration.personal_bank_tag_run_source",
                Set.of("SELECT", "INSERT"));
        privileges.put(
                "ti_migration.personal_bank_tag_receipt",
                Set.of("SELECT", "INSERT"));
        privileges.put(
                "ti_migration.personal_bank_tag_audit", Set.of());
        privileges.put("public.user_progress", Set.of("SELECT"));
        privileges.put(
                "public.user_question_tag_items", Set.of("SELECT", "INSERT"));
        return Map.copyOf(privileges);
    }

    static final class SchemaVerificationException extends Exception {
        private final FailureCode failureCode;

        SchemaVerificationException(FailureCode failureCode) {
            this(failureCode, null);
        }

        SchemaVerificationException(FailureCode failureCode, Throwable cause) {
            super("tag migration operator schema verification failed", cause);
            this.failureCode = Objects.requireNonNull(failureCode, "failureCode");
        }

        FailureCode failureCode() {
            return failureCode;
        }
    }
}
