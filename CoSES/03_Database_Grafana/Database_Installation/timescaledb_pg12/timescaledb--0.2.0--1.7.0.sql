-- Copyright (c) 2016-2018  Timescale, Inc. All Rights Reserved.
--
-- This file is licensed under the Apache License, see LICENSE-APACHE
-- at the top level directory of the TimescaleDB distribution.

-- This file is always prepended to all upgrade scripts.

-- Triggers should be disabled during upgrades to avoid having them
-- invoke functions that might load an old version of the shared
-- library before those functions have been updated.
DROP EVENT TRIGGER IF EXISTS timescaledb_ddl_command_end;
DROP EVENT TRIGGER IF EXISTS timescaledb_ddl_sql_drop;

-- These are legacy triggers. They need to be disabled here even
-- though they don't exist in newer versions, because they might still
-- exist when upgrading from older versions. Thus we need to DROP all
-- triggers here that have ever been created.
DROP TRIGGER IF EXISTS "0_cache_inval" ON _timescaledb_catalog.hypertable;
DROP TRIGGER IF EXISTS "0_cache_inval" ON _timescaledb_catalog.chunk;
DROP TRIGGER IF EXISTS "0_cache_inval" ON _timescaledb_catalog.chunk_constraint;
DROP TRIGGER IF EXISTS "0_cache_inval" ON _timescaledb_catalog.dimension_slice;
DROP TRIGGER IF EXISTS "0_cache_inval" ON _timescaledb_catalog.dimension;

CREATE OR REPLACE FUNCTION _timescaledb_internal.restart_background_workers()
RETURNS BOOL
AS '$libdir/timescaledb', 'ts_bgw_db_workers_restart'
LANGUAGE C VOLATILE;

SELECT _timescaledb_internal.restart_background_workers();
DROP FUNCTION IF EXISTS _timescaledb_internal.timescale_trigger_names();
DROP FUNCTION IF EXISTS _timescaledb_internal.main_table_insert_trigger() CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.main_table_after_insert_trigger() CASCADE;
ALTER TABLE IF EXISTS _timescaledb_catalog.dimension_slice
DROP CONSTRAINT dimension_slice_range_start_check,
DROP CONSTRAINT dimension_slice_range_end_check;
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_is_change_owner(pg_ddl_command);
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_change_owner_to(pg_ddl_command);

DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_add_constraints(integer);
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_process_alter_table() CASCADE;

CREATE INDEX ON _timescaledb_catalog.chunk_constraint(chunk_id, dimension_slice_id);

ALTER TABLE IF EXISTS _timescaledb_catalog.chunk_constraint
DROP CONSTRAINT chunk_constraint_pkey,
ADD COLUMN constraint_name NAME;

UPDATE _timescaledb_catalog.chunk_constraint cc
SET constraint_name =
  (SELECT con.conname FROM
   _timescaledb_catalog.chunk c
   INNER JOIN _timescaledb_catalog.dimension_slice ds ON (cc.dimension_slice_id = ds.id)
   INNER JOIN _timescaledb_catalog.dimension d ON (ds.dimension_id = d.id)
   INNER JOIN pg_constraint con ON (con.contype = 'c' AND con.conrelid = format('%I.%I',c.schema_name, c.table_name)::regclass)
   INNER JOIN pg_attribute att ON (att.attrelid = format('%I.%I',c.schema_name, c.table_name)::regclass AND att.attname = d.column_name)
   WHERE c.id = cc.chunk_id
   AND con.conname = format('constraint_%s', dimension_slice_id)
   AND array_length(con.conkey, 1) = 1 AND con.conkey = ARRAY[att.attnum]
   );

ALTER TABLE IF EXISTS _timescaledb_catalog.chunk_constraint
ALTER COLUMN constraint_name SET NOT NULL,
ALTER COLUMN dimension_slice_id DROP NOT NULL;

ALTER TABLE IF EXISTS _timescaledb_catalog.chunk_constraint
ADD COLUMN hypertable_constraint_name NAME NULL,
ADD CONSTRAINT chunk_constraint_chunk_id_constraint_name_key UNIQUE (chunk_id, constraint_name);

CREATE SEQUENCE _timescaledb_catalog.chunk_constraint_name;
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.chunk_constraint_name', '');

DROP FUNCTION IF EXISTS _timescaledb_internal.rename_hypertable(name, name, text, text);
DROP FUNCTION IF EXISTS create_hypertable(REGCLASS, NAME, NAME,INTEGER,NAME,NAME,BIGINT,BOOLEAN, BOOLEAN);
DROP FUNCTION IF EXISTS hypertable_relation_size(regclass);
DROP FUNCTION IF EXISTS chunk_relation_size(regclass);
DROP FUNCTION IF EXISTS indexes_relation_size(regclass);

---- Post script
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_create(INTEGER[], BIGINT[]) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_get(INTEGER[], BIGINT[]) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_create_after_lock(INTEGER[], BIGINT[]) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.dimension_calculate_default_range_closed(BIGINT, SMALLINT, BIGINT, OUT BIGINT, OUT BIGINT) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.dimension_calculate_default_range(INTEGER, BIGINT, OUT BIGINT, OUT BIGINT) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_calculate_new_ranges(INTEGER, BIGINT, INTEGER[], BIGINT[], BOOLEAN, OUT BIGINT, OUT BIGINT) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_id_get_by_dimensions(INTEGER[], BIGINT[]) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_get_dimensions_constraint_sql(INTEGER[], BIGINT[]) CASCADE;
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_get_dimension_constraint_sql(INTEGER, BIGINT) CASCADE;

--Makes sure the index is valid for a hypertable.
CREATE OR REPLACE FUNCTION _timescaledb_internal.check_index(index_oid REGCLASS, hypertable_row  _timescaledb_catalog.hypertable)
RETURNS VOID LANGUAGE plpgsql STABLE AS
$BODY$
DECLARE
    index_row       RECORD;
    missing_column  TEXT;
BEGIN
    SELECT * INTO STRICT index_row FROM pg_index WHERE indexrelid = index_oid;
    IF index_row.indisunique OR index_row.indisexclusion THEN
        -- unique/exclusion index must contain time and all partition dimension columns.

        -- get any partitioning columns that are not included in the index.
        SELECT d.column_name INTO missing_column
        FROM _timescaledb_catalog.dimension d
        WHERE d.hypertable_id = hypertable_row.id AND
              d.column_name NOT IN (
                SELECT attname
                FROM pg_attribute
                WHERE attrelid = index_row.indrelid AND
                attnum = ANY(index_row.indkey)
            );

        IF missing_column IS NOT NULL THEN
            RAISE EXCEPTION 'Cannot create a unique index without the column: % (used in partitioning)', missing_column
            USING ERRCODE = 'TS103';
        END IF;
    END IF;
END
$BODY$;

-- Creates a constraint on a chunk.
CREATE OR REPLACE FUNCTION _timescaledb_internal.chunk_constraint_add_table_constraint(
    chunk_constraint_row  _timescaledb_catalog.chunk_constraint
)
    RETURNS VOID LANGUAGE PLPGSQL AS
$BODY$
DECLARE
    sql_code    TEXT;
    chunk_row _timescaledb_catalog.chunk;
    hypertable_row _timescaledb_catalog.hypertable;
    constraint_oid OID;
    def TEXT;
BEGIN
    SELECT * INTO STRICT chunk_row FROM _timescaledb_catalog.chunk c WHERE c.id = chunk_constraint_row.chunk_id;
    SELECT * INTO STRICT hypertable_row FROM _timescaledb_catalog.hypertable h WHERE h.id = chunk_row.hypertable_id;

    IF chunk_constraint_row.dimension_slice_id IS NOT NULL THEN
        def := format('CHECK (%s)',  _timescaledb_internal.dimension_slice_get_constraint_sql(chunk_constraint_row.dimension_slice_id));
    ELSIF chunk_constraint_row.hypertable_constraint_name IS NOT NULL THEN
        SELECT oid INTO STRICT constraint_oid FROM pg_constraint
        WHERE conname=chunk_constraint_row.hypertable_constraint_name AND
              conrelid = format('%I.%I', hypertable_row.schema_name, hypertable_row.table_name)::regclass::oid;
        def := pg_get_constraintdef(constraint_oid);
    ELSE
        RAISE 'Unknown constraint type';
    END IF;

    sql_code := format(
        $$ ALTER TABLE %I.%I ADD CONSTRAINT %I %s $$,
        chunk_row.schema_name, chunk_row.table_name, chunk_constraint_row.constraint_name, def
    );
    EXECUTE sql_code;
END
$BODY$;

CREATE OR REPLACE FUNCTION _timescaledb_internal.create_chunk_constraint(
    chunk_id INTEGER,
    constraint_oid OID
)
    RETURNS VOID LANGUAGE PLPGSQL AS
$BODY$
DECLARE
    chunk_constraint_row _timescaledb_catalog.chunk_constraint;
    constraint_row pg_constraint;
    constraint_name TEXT;
    hypertable_constraint_name TEXT = NULL;
BEGIN
    SELECT * INTO STRICT constraint_row FROM pg_constraint WHERE OID = constraint_oid;
    hypertable_constraint_name := constraint_row.conname;
    constraint_name := format('%s_%s_%s', chunk_id,  nextval('_timescaledb_catalog.chunk_constraint_name'), hypertable_constraint_name);

    INSERT INTO _timescaledb_catalog.chunk_constraint (chunk_id, constraint_name, dimension_slice_id, hypertable_constraint_name)
    VALUES (chunk_id, constraint_name, NULL, hypertable_constraint_name) RETURNING * INTO STRICT chunk_constraint_row;

    PERFORM _timescaledb_internal.chunk_constraint_add_table_constraint(chunk_constraint_row);
END
$BODY$;

-- do I need to add a hypertable constraint to the chunks?;
CREATE OR REPLACE FUNCTION _timescaledb_internal.need_chunk_constraint(
    constraint_oid OID
)
    RETURNS BOOLEAN LANGUAGE PLPGSQL VOLATILE AS
$BODY$
DECLARE
    constraint_row record;
BEGIN
    SELECT * INTO STRICT constraint_row FROM pg_constraint WHERE OID = constraint_oid;

    IF constraint_row.contype IN ('c') THEN
        -- check and not null constraints handled by regular inheritance (from docs):
        --    All check constraints and not-null constraints on a parent table are automatically inherited by its children,
        --    unless explicitly specified otherwise with NO INHERIT clauses. Other types of constraints
        --    (unique, primary key, and foreign key constraints) are not inherited."

        IF constraint_row.connoinherit THEN
            RAISE 'NO INHERIT option not supported on hypertables: %', constraint_row.conname
            USING ERRCODE = 'TS101';
        END IF;

        RETURN FALSE;
    END IF;
    RETURN TRUE;
END
$BODY$;

CREATE OR REPLACE FUNCTION _timescaledb_internal.add_constraint(
    hypertable_id INTEGER,
    constraint_oid OID
)
    RETURNS VOID LANGUAGE PLPGSQL VOLATILE AS
$BODY$
DECLARE
    constraint_row pg_constraint;
    hypertable_row _timescaledb_catalog.hypertable;
BEGIN
    IF _timescaledb_internal.need_chunk_constraint(constraint_oid) THEN
        SELECT * INTO STRICT constraint_row FROM pg_constraint WHERE OID = constraint_oid;

        --check the validity of an index if a constraint uses an index
        --note: foreign-key constraints are excluded because they point to indexes on the foreign table /not/ the hypertable
        IF constraint_row.conindid <> 0 AND constraint_row.contype != 'f' THEN
            SELECT * INTO STRICT hypertable_row FROM _timescaledb_catalog.hypertable WHERE id = hypertable_id;
            PERFORM _timescaledb_internal.check_index(constraint_row.conindid, hypertable_row);
        END IF;

        PERFORM _timescaledb_internal.create_chunk_constraint(c.id, constraint_oid)
        FROM _timescaledb_catalog.chunk c
        WHERE c.hypertable_id = add_constraint.hypertable_id;
    END IF;
END
$BODY$;


SELECT _timescaledb_internal.add_constraint(h.id, c.oid)
FROM _timescaledb_catalog.hypertable h
INNER JOIN pg_constraint c ON (c.conrelid = format('%I.%I', h.schema_name, h.table_name)::regclass);

DELETE FROM _timescaledb_catalog.hypertable_index hi
WHERE EXISTS (
 SELECT 1 FROM pg_constraint WHERE conindid = format('%I.%I', hi.main_schema_name, hi.main_index_name)::regclass
);

ALTER TABLE IF EXISTS _timescaledb_catalog.chunk
DROP CONSTRAINT chunk_hypertable_id_fkey,
ADD CONSTRAINT chunk_hypertable_id_fkey
  FOREIGN KEY (hypertable_id)
  REFERENCES _timescaledb_catalog.hypertable(id);

ALTER TABLE IF EXISTS  _timescaledb_catalog.chunk_constraint
DROP CONSTRAINT chunk_constraint_chunk_id_fkey,
ADD CONSTRAINT chunk_constraint_chunk_id_fkey
  FOREIGN KEY (chunk_id)
  REFERENCES _timescaledb_catalog.chunk(id);

ALTER TABLE IF EXISTS  _timescaledb_catalog.chunk_constraint
DROP CONSTRAINT chunk_constraint_dimension_slice_id_fkey,
ADD CONSTRAINT chunk_constraint_dimension_slice_id_fkey
  FOREIGN KEY (dimension_slice_id)
  REFERENCES _timescaledb_catalog.dimension_slice(id);


DROP EVENT TRIGGER IF EXISTS ddl_check_drop_command;

DROP TRIGGER IF EXISTS trigger_main_on_change_chunk ON _timescaledb_catalog.chunk;

DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_create_table(int);
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_process_drop_table();
DROP FUNCTION IF EXISTS _timescaledb_internal.on_change_chunk();
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_hypertable(name, name);

DROP EVENT TRIGGER IF EXISTS ddl_create_trigger;
DROP EVENT TRIGGER IF EXISTS ddl_drop_trigger;

DROP FUNCTION IF EXISTS _timescaledb_internal.add_trigger(int, oid);
DROP FUNCTION IF EXISTS _timescaledb_internal.create_chunk_trigger(int, name, text);
DROP FUNCTION IF EXISTS _timescaledb_internal.create_trigger_on_all_chunks(int, name, text);
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_process_create_trigger();
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_process_drop_trigger();
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunk_trigger(int, name);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_trigger_on_all_chunks(INTEGER, NAME);
DROP FUNCTION IF EXISTS _timescaledb_internal.get_general_trigger_definition(regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.get_trigger_definition_for_table(INTEGER, text);
DROP FUNCTION IF EXISTS _timescaledb_internal.need_chunk_trigger(int, oid);

-- Adding this in the update script because aggregates.sql is not rerun in case of an update
CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_sfunc (state INTERNAL, val DOUBLE PRECISION, MIN DOUBLE PRECISION, MAX DOUBLE PRECISION, nbuckets INTEGER)
RETURNS INTERNAL
AS '$libdir/timescaledb-1.7.0', 'ts_hist_sfunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_combinefunc(state1 INTERNAL, state2 INTERNAL)
RETURNS INTERNAL
AS '$libdir/timescaledb-1.7.0', 'ts_hist_combinefunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_serializefunc(INTERNAL)
RETURNS bytea
AS '$libdir/timescaledb-1.7.0', 'ts_hist_serializefunc'
LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_deserializefunc(bytea, INTERNAL)
RETURNS INTERNAL
AS '$libdir/timescaledb-1.7.0', 'ts_hist_deserializefunc'
LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_finalfunc(state INTERNAL, val DOUBLE PRECISION, MIN DOUBLE PRECISION, MAX DOUBLE PRECISION, nbuckets INTEGER)
RETURNS INTEGER[]
AS '$libdir/timescaledb-1.7.0', 'ts_hist_finalfunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

-- This aggregate partitions the dataset into a specified number of buckets (nbuckets) ranging
-- from the inputted min to max values.
CREATE AGGREGATE histogram (DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, INTEGER) (
    SFUNC = _timescaledb_internal.hist_sfunc,
    STYPE = INTERNAL,
    COMBINEFUNC = _timescaledb_internal.hist_combinefunc,
    SERIALFUNC = _timescaledb_internal.hist_serializefunc,
    DESERIALFUNC = _timescaledb_internal.hist_deserializefunc,
    PARALLEL = SAFE,
    FINALFUNC = _timescaledb_internal.hist_finalfunc,
    FINALFUNC_EXTRA
);
DROP FUNCTION IF EXISTS public.time_bucket(INTERVAL, TIMESTAMP);
DROP FUNCTION IF EXISTS public.time_bucket(INTERVAL, TIMESTAMPTZ);
DROP FUNCTION IF EXISTS public.time_bucket(INTERVAL, DATE);
DROP FUNCTION IF EXISTS public.time_bucket(INTERVAL, TIMESTAMP, INTERVAL);
DROP FUNCTION IF EXISTS public.time_bucket(INTERVAL, TIMESTAMPTZ, INTERVAL);
DROP FUNCTION IF EXISTS public.time_bucket(INTERVAL, DATE, INTERVAL);
DROP FUNCTION IF EXISTS public.time_bucket(BIGINT, BIGINT);
DROP FUNCTION IF EXISTS public.time_bucket(INT, INT);
DROP FUNCTION IF EXISTS public.time_bucket(SMALLINT, SMALLINT);
DROP FUNCTION IF EXISTS public.time_bucket(BIGINT, BIGINT, BIGINT);
DROP FUNCTION IF EXISTS public.time_bucket(INT, INT, INT);
DROP FUNCTION IF EXISTS public.time_bucket(SMALLINT, SMALLINT, SMALLINT);

-- Indexing updates
DROP EVENT TRIGGER IF EXISTS ddl_create_index;
DROP EVENT TRIGGER IF EXISTS ddl_alter_index;
DROP EVENT TRIGGER IF EXISTS ddl_drop_index;
DROP TRIGGER IF EXISTS trigger_main_on_change_chunk_index ON _timescaledb_catalog.chunk_index;
DROP TRIGGER IF EXISTS trigger_main_on_change_hypertable_index ON _timescaledb_catalog.hypertable_index;

DROP FUNCTION IF EXISTS _timescaledb_internal.get_index_definition_for_table(NAME, NAME, NAME, TEXT);
DROP FUNCTION IF EXISTS _timescaledb_internal.create_chunk_index_row(NAME, NAME, NAME, NAME, TEXT);
DROP FUNCTION IF EXISTS _timescaledb_internal.on_change_chunk_index();
DROP FUNCTION IF EXISTS _timescaledb_internal.add_index(INTEGER, NAME, NAME, TEXT);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_index(NAME, NAME);
DROP FUNCTION IF EXISTS _timescaledb_internal.get_general_index_definition(REGCLASS, REGCLASS, _timescaledb_catalog.hypertable);
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_process_create_index();
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_process_alter_index();
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_process_drop_index();
DROP FUNCTION IF EXISTS _timescaledb_internal.create_index_on_all_chunks(INTEGER, NAME, NAME, TEXT);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_index_on_all_chunks(NAME, NAME);
DROP FUNCTION IF EXISTS _timescaledb_internal.on_change_hypertable_index();
DROP FUNCTION IF EXISTS _timescaledb_internal.need_chunk_index(INTEGER, OID);
DROP FUNCTION IF EXISTS _timescaledb_internal.check_index(REGCLASS, _timescaledb_catalog.hypertable);

DROP FUNCTION IF EXISTS indexes_relation_size_pretty(REGCLASS);

ALTER TABLE IF EXISTS _timescaledb_catalog.chunk_index RENAME TO chunk_index_old;
ALTER SEQUENCE IF EXISTS _timescaledb_catalog.chunk_index_id_seq RENAME TO chunk_index_old_id_seq;

-- Create new table
CREATE TABLE IF NOT EXISTS _timescaledb_catalog.chunk_index (
    chunk_id              INTEGER NOT NULL REFERENCES _timescaledb_catalog.chunk(id) ON DELETE CASCADE,
    index_name            NAME NOT NULL,
    hypertable_id         INTEGER NOT NULL REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
    hypertable_index_name NAME NOT NULL,
    UNIQUE(chunk_id, index_name)
);
CREATE INDEX IF NOT EXISTS chunk_index_hypertable_id_hypertable_index_name_idx
ON _timescaledb_catalog.chunk_index(hypertable_id, hypertable_index_name);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.chunk_index', '');

-- Remove metadata table triggers
DROP TRIGGER trigger_block_truncate ON _timescaledb_catalog.hypertable;
DROP TRIGGER trigger_block_truncate ON _timescaledb_catalog.dimension;
DROP TRIGGER trigger_block_truncate ON _timescaledb_catalog.dimension_slice;
DROP TRIGGER trigger_block_truncate ON _timescaledb_catalog.chunk_constraint;
DROP TRIGGER trigger_block_truncate ON _timescaledb_catalog.hypertable_index;
DROP TRIGGER trigger_1_main_on_change_hypertable ON _timescaledb_catalog.hypertable;
DROP FUNCTION IF EXISTS _timescaledb_internal.on_truncate_block();
DROP FUNCTION IF EXISTS _timescaledb_internal.on_trigger_error(TEXT, NAME, NAME);
DROP FUNCTION IF EXISTS _timescaledb_internal.on_change_hypertable();
DROP FUNCTION IF EXISTS _timescaledb_internal.setup_main(BOOLEAN);
DROP FUNCTION IF EXISTS restore_timescaledb();

DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunk(INTEGER, BOOLEAN, BOOLEAN);
DROP FUNCTION IF EXISTS drop_chunks(TIMESTAMPTZ, NAME, NAME);
DROP FUNCTION IF EXISTS drop_chunks(INTERVAL, NAME, NAME);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunks_older_than(BIGINT, NAME, NAME);
DROP FUNCTION IF EXISTS _timescaledb_internal.truncate_hypertable(NAME, NAME);

--- Post script
-- Indexing updates

-- Convert old chunk_index table data to new format
INSERT INTO _timescaledb_catalog.chunk_index
SELECT ch.id, ci.index_name, h.id, ci.main_index_name
FROM _timescaledb_catalog.chunk_index_old ci,
     _timescaledb_catalog.hypertable h,
     _timescaledb_catalog.chunk ch,
     pg_index i,
     pg_class c
WHERE ci.schema_name = ch.schema_name
AND   ci.table_name = ch.table_name
AND   i.indexrelid = format('%I.%I', ci.main_schema_name, ci.main_index_name)::REGCLASS
AND   i.indrelid = c.oid
AND   ci.main_schema_name = h.schema_name
AND   c.relname = h.table_name;

ALTER EXTENSION timescaledb
DROP TABLE _timescaledb_catalog.chunk_index_old;
ALTER EXTENSION timescaledb
DROP TABLE _timescaledb_catalog.hypertable_index;
ALTER EXTENSION timescaledb
DROP SEQUENCE _timescaledb_catalog.chunk_index_old_id_seq;

DROP TABLE IF EXISTS _timescaledb_catalog.chunk_index_old;
DROP TABLE IF EXISTS _timescaledb_catalog.hypertable_index;
-- No need to drop _timescaledb_catalog.chunk_index_old_id_seq,
-- removed with table.
DROP FUNCTION IF EXISTS drop_chunks(INTEGER, NAME, NAME, BOOLEAN);

DROP FUNCTION IF EXISTS _timescaledb_internal.create_chunk_constraint(integer,oid);
DROP FUNCTION IF EXISTS _timescaledb_internal.add_constraint(integer,oid);
DROP FUNCTION IF EXISTS _timescaledb_internal.add_constraint_by_name(integer,name);
DROP FUNCTION IF EXISTS _timescaledb_internal.need_chunk_constraint(oid);

INSERT INTO _timescaledb_catalog.chunk_index (chunk_id, index_name, hypertable_id, hypertable_index_name)
SELECT chunk_con.chunk_id, pg_chunk_index_class.relname, chunk.hypertable_id, pg_hypertable_index_class.relname
FROM _timescaledb_catalog.chunk_constraint chunk_con
INNER JOIN _timescaledb_catalog.chunk chunk ON (chunk_con.chunk_id = chunk.id)
INNER JOIN _timescaledb_catalog.hypertable hypertable ON (chunk.hypertable_id = hypertable.id)
INNER JOIN pg_constraint pg_chunk_con ON (
        pg_chunk_con.conrelid = format('%I.%I', chunk.schema_name, chunk.table_name)::regclass
        AND pg_chunk_con.conname = chunk_con.constraint_name
        AND pg_chunk_con.contype != 'f'
)
INNER JOIN pg_class pg_chunk_index_class ON (
    pg_chunk_con.conindid = pg_chunk_index_class.oid
)
INNER JOIN pg_constraint pg_hypertable_con ON (
        pg_hypertable_con.conrelid = format('%I.%I', hypertable.schema_name, hypertable.table_name)::regclass
        AND pg_hypertable_con.conname = chunk_con.hypertable_constraint_name
)
INNER JOIN pg_class pg_hypertable_index_class ON (
    pg_hypertable_con.conindid = pg_hypertable_index_class.oid
);

UPDATE _timescaledb_catalog.dimension_slice SET range_end = 9223372036854775807 WHERE range_end = 2147483647;
UPDATE _timescaledb_catalog.dimension_slice SET range_start = -9223372036854775808 WHERE range_start = 0;

DROP FUNCTION IF EXISTS _timescaledb_internal.range_value_to_pretty(BIGINT, regtype);

-- Upgrade support for setting partitioning function
DROP FUNCTION IF EXISTS create_hypertable(regclass,name,name,integer,name,name,anyelement,boolean,boolean);
DROP FUNCTION IF EXISTS add_dimension(regclass,name,integer,bigint);
DROP FUNCTION IF EXISTS _timescaledb_internal.create_hypertable_row(regclass,name,name,name,name,integer,name,name,bigint,name);
DROP FUNCTION IF EXISTS _timescaledb_internal.add_dimension(regclass,_timescaledb_catalog.hypertable,name,integer,bigint,boolean);

--- Post script

CREATE OR REPLACE FUNCTION _timescaledb_internal.set_time_columns_not_null()
    RETURNS VOID LANGUAGE PLPGSQL VOLATILE AS
$BODY$
DECLARE
        ht_time_column RECORD;
BEGIN

        FOR ht_time_column IN
        SELECT ht.schema_name, ht.table_name, d.column_name
        FROM _timescaledb_catalog.hypertable ht, _timescaledb_catalog.dimension d
        WHERE ht.id = d.hypertable_id AND d.partitioning_func IS NULL
        LOOP
                EXECUTE format(
                $$
                ALTER TABLE %I.%I ALTER %I SET NOT NULL
                $$, ht_time_column.schema_name, ht_time_column.table_name, ht_time_column.column_name);
        END LOOP;
END
$BODY$;

SELECT _timescaledb_internal.set_time_columns_not_null();

CREATE OR REPLACE FUNCTION _timescaledb_internal.to_unix_microseconds(ts TIMESTAMPTZ) RETURNS BIGINT
    AS '$libdir/timescaledb-1.7.0', 'ts_pg_timestamp_to_unix_microseconds' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.to_timestamp(unixtime_us BIGINT) RETURNS TIMESTAMPTZ
    AS '$libdir/timescaledb-1.7.0', 'ts_pg_unix_microseconds_to_timestamp' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.dimension_is_finite(
    val      BIGINT
)
    RETURNS BOOLEAN LANGUAGE SQL IMMUTABLE PARALLEL SAFE AS
$BODY$
    --end values of bigint reserved for infinite
    SELECT val > (-9223372036854775808)::bigint AND val < 9223372036854775807::bigint
$BODY$;

CREATE OR REPLACE FUNCTION _timescaledb_internal.dimension_slice_get_constraint_sql(
    dimension_slice_id  INTEGER
)
    RETURNS TEXT LANGUAGE PLPGSQL VOLATILE AS
$BODY$
DECLARE
    dimension_slice_row _timescaledb_catalog.dimension_slice;
    dimension_row _timescaledb_catalog.dimension;
    parts TEXT[];
BEGIN
    SELECT * INTO STRICT dimension_slice_row
    FROM _timescaledb_catalog.dimension_slice
    WHERE id = dimension_slice_id;

    SELECT * INTO STRICT dimension_row
    FROM _timescaledb_catalog.dimension
    WHERE id = dimension_slice_row.dimension_id;

    IF dimension_row.partitioning_func IS NOT NULL THEN

        IF  _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_start) THEN
            parts = parts || format(
            $$
                %1$I.%2$I(%3$I) >= %4$L
            $$,
            dimension_row.partitioning_func_schema,
            dimension_row.partitioning_func,
            dimension_row.column_name,
            dimension_slice_row.range_start);
        END IF;

        IF _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_end) THEN
            parts = parts || format(
            $$
                %1$I.%2$I(%3$I) < %4$L
            $$,
            dimension_row.partitioning_func_schema,
            dimension_row.partitioning_func,
            dimension_row.column_name,
            dimension_slice_row.range_end);
        END IF;

        return array_to_string(parts, 'AND');
    ELSE
        --TODO: only works with time for now
        IF _timescaledb_internal.time_literal_sql(dimension_slice_row.range_start, dimension_row.column_type) =
           _timescaledb_internal.time_literal_sql(dimension_slice_row.range_end, dimension_row.column_type) THEN
            RAISE 'Time based constraints have the same start and end values for column "%": %',
                    dimension_row.column_name,
                    _timescaledb_internal.time_literal_sql(dimension_slice_row.range_end, dimension_row.column_type);
        END IF;

        parts = ARRAY[]::text[];

        IF _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_start) THEN
            parts = parts || format(
            $$
                 %1$I >= %2$s
            $$,
            dimension_row.column_name,
            _timescaledb_internal.time_literal_sql(dimension_slice_row.range_start, dimension_row.column_type));
        END IF;

        IF _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_end) THEN
            parts = parts || format(
            $$
                 %1$I < %2$s
            $$,
            dimension_row.column_name,
            _timescaledb_internal.time_literal_sql(dimension_slice_row.range_end, dimension_row.column_type));
        END IF;

        return array_to_string(parts, 'AND');
    END IF;
END
$BODY$;

--has to be done since old range_end for the CHECK constraint was 2147483647 on closed partitions.
DO $$
DECLARE
    chunk_constraint_row  _timescaledb_catalog.chunk_constraint;
    chunk_row _timescaledb_catalog.chunk;
BEGIN
    -- Need to do this update in two loops: first remove constraints, then add back.
    -- This is because we can only remove the old partitioning function when
    -- there are no constraints on the tables referencing the old function
    FOR chunk_constraint_row IN
        SELECT cc.*
        FROM _timescaledb_catalog.chunk_constraint cc
        INNER JOIN  _timescaledb_catalog.dimension_slice ds ON (cc.dimension_slice_id = ds.id)
        INNER JOIN  _timescaledb_catalog.dimension d ON (ds.dimension_id = d.id)
        WHERE d.partitioning_func IS NOT NULL
    LOOP
        SELECT * INTO STRICT chunk_row FROM _timescaledb_catalog.chunk c WHERE c.id = chunk_constraint_row.chunk_id;

        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT %I', chunk_row.schema_name, chunk_row.table_name, chunk_constraint_row.constraint_name);
    END LOOP;

    RAISE NOTICE 'Updating constraints';

    DROP FUNCTION IF EXISTS _timescaledb_internal.get_partition_for_key(text);
    CREATE OR REPLACE FUNCTION _timescaledb_internal.get_partition_for_key(val anyelement)
    RETURNS int
    AS '$libdir/timescaledb-1.7.0', 'ts_get_partition_for_key' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

    FOR chunk_constraint_row IN
        SELECT cc.*
        FROM _timescaledb_catalog.chunk_constraint cc
        INNER JOIN  _timescaledb_catalog.dimension_slice ds ON (cc.dimension_slice_id = ds.id)
        INNER JOIN  _timescaledb_catalog.dimension d ON (ds.dimension_id = d.id)
        WHERE d.partitioning_func IS NOT NULL
    LOOP
        SELECT * INTO STRICT chunk_row FROM _timescaledb_catalog.chunk c WHERE c.id = chunk_constraint_row.chunk_id;
        PERFORM _timescaledb_internal.chunk_constraint_add_table_constraint(chunk_constraint_row);
    END LOOP;

END$$;

--for timestamp (non-tz) columns we used to have internal_time -> constraint_time via local_time.
--So the internal time was interpreted as UTC but the constraint was printed in terms of the local time.
--Now we interpret the internal_time as UTC and the constraints is generated as UTC as well.
--These constraints should not be re-written since they are correct for the data. But we should adjust the internal time
--to be consistent.

-- So _timescaledb_internal.to_timestamp(internal_time)::timestamp gives you the old constraint
-- We then convert it to timestamptz as though it was at UTC
-- finally, we convert it to the internal represtentation back.

UPDATE _timescaledb_catalog.dimension_slice ds
SET
range_end = _timescaledb_internal.to_unix_microseconds(timezone('UTC',_timescaledb_internal.to_timestamp(range_end)::timestamp)),
range_start = _timescaledb_internal.to_unix_microseconds(timezone('UTC',_timescaledb_internal.to_timestamp(range_start)::timestamp))
FROM _timescaledb_catalog.dimension d
WHERE ds.dimension_id = d.id AND d.column_type = 'timestamp'::regtype;
DROP FUNCTION IF EXISTS _timescaledb_internal.create_hypertable_row(REGCLASS, NAME, NAME, NAME, NAME, INTEGER, NAME, NAME, BIGINT, NAME, REGPROC);
DROP FUNCTION IF EXISTS _timescaledb_internal.rename_hypertable(NAME, NAME, NAME, NAME);

DROP FUNCTION IF EXISTS drop_chunks(bigint,name,name,boolean);
DROP FUNCTION IF EXISTS drop_chunks(timestamptz,name,name,boolean);
DROP FUNCTION IF EXISTS _timescaledb_cache.invalidate_relcache(oid);

DROP FUNCTION IF EXISTS set_chunk_time_interval(REGCLASS, BIGINT);
DROP FUNCTION IF EXISTS add_dimension(REGCLASS, NAME, INTEGER, BIGINT, REGPROC);
DROP FUNCTION IF EXISTS _timescaledb_internal.add_dimension(REGCLASS, _timescaledb_catalog.hypertable, NAME, INTEGER, BIGINT, REGPROC, BOOLEAN);
DROP FUNCTION IF EXISTS _timescaledb_internal.time_interval_specification_to_internal(REGTYPE, anyelement, INTERVAL, TEXT);

-- Tablespace changes
DROP FUNCTION IF EXISTS _timescaledb_internal.attach_tablespace(integer, name);
DROP FUNCTION IF EXISTS attach_tablespace(regclass, name);
-- Cache invalidation functions and triggers
DROP FUNCTION IF EXISTS _timescaledb_cache.invalidate_relcache_trigger();
DROP FUNCTION IF EXISTS _timescaledb_cache.invalidate_relcache(regclass);

-- Tablespace changes
DROP FUNCTION IF EXISTS _timescaledb_internal.select_tablespace(integer, integer[]);
DROP FUNCTION IF EXISTS _timescaledb_internal.select_tablespace(integer, integer);
DROP FUNCTION IF EXISTS _timescaledb_internal.select_tablespace(integer);

-- Chunk functions
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_create(integer, integer, name, name);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunk_metadata(int);

-- Chunk constraint functions
DROP FUNCTION IF EXISTS _timescaledb_internal.create_chunk_constraint(integer, oid);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_constraint(integer, name);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunk_constraint(integer, name, boolean);
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_constraint_drop_table_constraint(_timescaledb_catalog.chunk_constraint);

-- Dimension and time functions
DROP FUNCTION IF EXISTS _timescaledb_internal.change_column_type(int, name, regtype);
DROP FUNCTION IF EXISTS _timescaledb_internal.rename_column(int, name, name);
DROP FUNCTION IF EXISTS _timescaledb_internal.set_time_column_constraint(regclass, name);
DROP FUNCTION IF EXISTS _timescaledb_internal.add_dimension(regclass, _timescaledb_catalog.hypertable, name, integer, anyelement, regproc, boolean, boolean);
DROP FUNCTION IF EXISTS add_dimension(regclass, name, integer, anyelement, regproc);
DROP FUNCTION IF EXISTS _timescaledb_internal.time_interval_specification_to_internal(regtype, anyelement, interval, text, boolean);
DROP FUNCTION IF EXISTS _timescaledb_internal.time_interval_specification_to_internal_with_default_time(regtype, anyelement, text, boolean);
DROP FUNCTION IF EXISTS _timescaledb_internal.create_hypertable(regclass, name, name, name, name, integer, name, name, bigint, name, boolean, regproc);
DROP FUNCTION IF EXISTS create_hypertable(regclass,name,name,integer,name,name,anyelement,boolean,boolean,regproc);
DROP FUNCTION IF EXISTS set_chunk_time_interval(regclass, anyelement);

-- Hypertable and related functions
DROP FUNCTION IF EXISTS _timescaledb_internal.set_time_columns_not_null();
DROP FUNCTION IF EXISTS _timescaledb_internal.create_schema(name);
DROP FUNCTION IF EXISTS _timescaledb_internal.check_role(regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.attach_tablespace(name,regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.create_default_indexes(_timescaledb_catalog.hypertable,regclass,name);
DROP FUNCTION IF EXISTS _timescaledb_internal.create_hypertable_schema(name);
DROP FUNCTION IF EXISTS _timescaledb_internal.detach_tablespace(name,regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.detach_tablespaces(regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.dimension_type(regclass,name,boolean);
DROP FUNCTION IF EXISTS _timescaledb_internal.show_tablespaces(regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.verify_hypertable_indexes(regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.validate_triggers(regclass);
DROP FUNCTION IF EXISTS _timescaledb_internal.chunk_create_table(int, name);
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_change_owner(oid, name);
DROP FUNCTION IF EXISTS _timescaledb_internal.truncate_hypertable(name,name,boolean);
DROP FUNCTION IF EXISTS attach_tablespace(name,regclass);
DROP FUNCTION IF EXISTS detach_tablespace(name,regclass);

-- Remove redundant index
DROP INDEX IF EXISTS _timescaledb_catalog.dimension_slice_dimension_id_range_start_range_end_idx;

DROP FUNCTION IF EXISTS _timescaledb_internal.drop_hypertable(int,boolean);

DELETE FROM _timescaledb_catalog.dimension_slice WHERE id IN
(SELECT ds.id FROM _timescaledb_catalog.chunk_constraint cc
 RIGHT JOIN _timescaledb_catalog.dimension_slice ds
 ON (ds.id = cc.dimension_slice_id)
 WHERE dimension_slice_id IS NULL);

-- Post script
DROP FUNCTION IF EXISTS _timescaledb_internal.ddl_command_end();
--Fix any potential catalog issues that may have been introduced if a
--trigger was dropped on a hypertable before the current bugfix
--Only deletes orphaned rows from pg_depend.
DELETE FROM pg_depend d 
WHERE d.classid = 'pg_trigger'::regclass 
AND NOT EXISTS (SELECT 1 FROM pg_trigger WHERE oid = d.objid);
-- Adaptive chunking
CREATE OR REPLACE FUNCTION _timescaledb_internal.calculate_chunk_interval(
        dimension_id INTEGER,
        dimension_coord BIGINT,
        chunk_target_size BIGINT
) RETURNS BIGINT AS '$libdir/timescaledb-1.7.0', 'ts_calculate_chunk_interval' LANGUAGE C;

ALTER TABLE _timescaledb_catalog.hypertable ADD COLUMN chunk_sizing_func_schema NAME;
ALTER TABLE _timescaledb_catalog.hypertable ADD COLUMN chunk_sizing_func_name NAME;
ALTER TABLE _timescaledb_catalog.hypertable ADD COLUMN chunk_target_size BIGINT CHECK (chunk_target_size >= 0);
UPDATE _timescaledb_catalog.hypertable SET chunk_target_size = 0;
UPDATE _timescaledb_catalog.hypertable SET chunk_sizing_func_schema = '_timescaledb_internal';
UPDATE _timescaledb_catalog.hypertable SET chunk_sizing_func_name = 'calculate_chunk_interval';
ALTER TABLE _timescaledb_catalog.hypertable ALTER COLUMN chunk_target_size SET NOT NULL;
ALTER TABLE _timescaledb_catalog.hypertable ALTER COLUMN chunk_sizing_func_schema SET NOT NULL;
ALTER TABLE _timescaledb_catalog.hypertable ALTER COLUMN chunk_sizing_func_name SET NOT NULL;

DROP FUNCTION IF EXISTS create_hypertable(regclass,name,name,integer,name,name,anyelement,boolean,boolean,regproc,boolean);
DROP FUNCTION IF EXISTS _timescaledb_internal.time_to_internal(anyelement,regtype);
-- Trigger that blocks INSERTs on the hypertable's root table
CREATE OR REPLACE FUNCTION _timescaledb_internal.insert_blocker() RETURNS trigger
AS '$libdir/timescaledb-1.7.0', 'ts_hypertable_insert_blocker' LANGUAGE C;

-- Drop all pre-0.11.1 insert_blockers from hypertables and add the new, visible trigger
CREATE FUNCTION _timescaledb_internal.insert_blocker_trigger_add(relid REGCLASS) RETURNS OID
AS '$libdir/timescaledb-1.7.0', 'ts_hypertable_insert_blocker_trigger_add' LANGUAGE C VOLATILE STRICT;

SELECT _timescaledb_internal.insert_blocker_trigger_add(h.relid)
FROM (SELECT format('%I.%I', schema_name, table_name)::regclass AS relid FROM _timescaledb_catalog.hypertable) AS h;

DROP FUNCTION _timescaledb_internal.insert_blocker_trigger_add(REGCLASS);

CREATE SCHEMA IF NOT EXISTS _timescaledb_config;
GRANT USAGE ON SCHEMA _timescaledb_config TO PUBLIC;

CREATE SEQUENCE IF NOT EXISTS _timescaledb_config.bgw_job_id_seq MINVALUE 1000;
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_config.bgw_job_id_seq', '');

CREATE TABLE IF NOT EXISTS _timescaledb_config.bgw_job (
    id                  INTEGER PRIMARY KEY DEFAULT nextval('_timescaledb_config.bgw_job_id_seq'),
    application_name    NAME        NOT NULL,
    job_type            NAME        NOT NULL,
    schedule_interval   INTERVAL    NOT NULL,
    max_runtime         INTERVAL    NOT NULL,
    max_retries         INT         NOT NULL,
    retry_period        INTERVAL    NOT NULL,
    CONSTRAINT  valid_job_type CHECK (job_type IN ('telemetry_and_version_check_if_enabled'))
);
ALTER SEQUENCE _timescaledb_config.bgw_job_id_seq OWNED BY _timescaledb_config.bgw_job.id;

SELECT pg_catalog.pg_extension_config_dump('_timescaledb_config.bgw_job', 'WHERE id >= 1000');

CREATE TABLE IF NOT EXISTS _timescaledb_internal.bgw_job_stat (
    job_id                  INT         PRIMARY KEY REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
    last_start              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_finish             TIMESTAMPTZ NOT NULL,
    next_start              TIMESTAMPTZ NOT NULL,
    last_run_success        BOOL        NOT NULL,
    total_runs              BIGINT      NOT NULL,
    total_duration          INTERVAL    NOT NULL,
    total_successes         BIGINT      NOT NULL,
    total_failures          BIGINT      NOT NULL,
    total_crashes           BIGINT      NOT NULL,
    consecutive_failures    INT         NOT NULL,
    consecutive_crashes     INT         NOT NULL
);
--The job_stat table is not dumped by pg_dump on purpose because
--the statistics probably aren't very meaningful across instances.

GRANT SELECT ON _timescaledb_config.bgw_job TO PUBLIC;
GRANT SELECT ON _timescaledb_internal.bgw_job_stat TO PUBLIC;

DO language plpgsql $$
BEGIN
  RAISE WARNING '%',
 E'\nStarting in v0.12.0, TimescaleDB collects anonymous reports to better understand and assist our
users. For more information and how to disable, please see our docs https://docs.timescaledb.com/using-timescaledb/telemetry.\n';
END;
$$;

CREATE TABLE IF NOT EXISTS _timescaledb_catalog.installation_metadata (
    key     NAME NOT NULL PRIMARY KEY,
    value   TEXT NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.installation_metadata', $$WHERE key='exported_uuid'$$);

INSERT INTO _timescaledb_catalog.installation_metadata SELECT 'install_timestamp', to_timestamp(0);
DROP INDEX IF EXISTS _timescaledb_catalog.dimension_hypertable_id_idx;

GRANT USAGE ON SCHEMA _timescaledb_cache TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA _timescaledb_catalog TO PUBLIC;
GRANT SELECT ON TABLE _timescaledb_internal.bgw_job_stat TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA _timescaledb_catalog TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA _timescaledb_config TO PUBLIC;

DROP FUNCTION IF EXISTS create_hypertable(regclass,name,name,integer,name,name,anyelement,boolean,boolean,regproc,boolean,text,regproc);
DROP FUNCTION IF EXISTS add_dimension(regclass,name,integer,anyelement,regproc,boolean);

DROP FUNCTION IF EXISTS _timescaledb_internal.get_version();
DROP FUNCTION IF EXISTS drop_chunks(INTERVAL, NAME, NAME, BOOLEAN);
DROP FUNCTION IF EXISTS drop_chunks(ANYELEMENT, NAME, NAME, BOOLEAN);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunks_impl(BIGINT, NAME, NAME, BOOLEAN, BOOLEAN);
DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunks_type_check(REGTYPE, NAME, NAME);
DROP FUNCTION IF EXISTS _timescaledb_internal.dimension_get_time(INTEGER);
DROP FUNCTION IF EXISTS create_hypertable(regclass, name, name, integer, name, name, anyelement, boolean, boolean, regproc, boolean, text, regproc);
DROP FUNCTION IF EXISTS _timescaledb_internal.to_microseconds(TIMESTAMPTZ);
DROP FUNCTION IF EXISTS _timescaledb_internal.to_timestamp_pg(BIGINT);
DROP FUNCTION IF EXISTS _timescaledb_internal.time_to_internal(anyelement);
--Now we define the argument tables for available BGW policies.
CREATE TABLE IF NOT EXISTS _timescaledb_config.bgw_policy_reorder (
    job_id          		INTEGER     PRIMARY KEY REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
    hypertable_id   		INTEGER     UNIQUE NOT NULL    REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
	hypertable_index_name	NAME		NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_config.bgw_policy_reorder', '');

CREATE TABLE IF NOT EXISTS _timescaledb_config.bgw_policy_drop_chunks (
    job_id          		INTEGER     PRIMARY KEY REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
    hypertable_id   		INTEGER     UNIQUE NOT NULL REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
	older_than				INTERVAL    NOT NULL,
	cascade					BOOLEAN
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_config.bgw_policy_drop_chunks', '');

----- End BGW policy table definitions

-- Now we define a special stats table for each job/chunk pair. This will be used by the scheduler
-- to determine whether to run a specific job on a specific chunk.
CREATE TABLE IF NOT EXISTS _timescaledb_internal.bgw_policy_chunk_stats (
	job_id					INTEGER 	NOT NULL REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
	chunk_id				INTEGER		NOT NULL REFERENCES _timescaledb_catalog.chunk(id) ON DELETE CASCADE,
	num_times_job_run		INTEGER,
	last_time_job_run		TIMESTAMPTZ,
	UNIQUE(job_id,chunk_id)
);

GRANT SELECT ON _timescaledb_config.bgw_policy_reorder TO PUBLIC;
GRANT SELECT ON _timescaledb_config.bgw_policy_drop_chunks TO PUBLIC;
GRANT SELECT ON _timescaledb_internal.bgw_policy_chunk_stats TO PUBLIC;

DROP FUNCTION IF EXISTS _timescaledb_internal.drop_chunks_impl(REGCLASS, "any", "any", BOOLEAN);
DROP FUNCTION IF EXISTS drop_chunks("any", NAME, NAME, BOOLEAN, "any");

DROP FUNCTION IF EXISTS _timescaledb_internal.get_os_info();

-- we add an addition optional argument to locf
DROP FUNCTION IF EXISTS locf(ANYELEMENT,ANYELEMENT);

CREATE TABLE IF NOT EXISTS _timescaledb_catalog.continuous_agg (
    mat_hypertable_id INTEGER PRIMARY KEY REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
    raw_hypertable_id INTEGER NOT NULL REFERENCES  _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
    user_view_schema NAME NOT NULL,
    user_view_name NAME NOT NULL,
    partial_view_schema NAME NOT NULL,
    partial_view_name NAME NOT NULL,
    bucket_width  BIGINT NOT NULL,
    job_id INTEGER UNIQUE NOT NULL REFERENCES _timescaledb_config.bgw_job(id) ON DELETE RESTRICT,
    refresh_lag BIGINT NOT NULL,
    direct_view_schema NAME NOT NULL,
    direct_view_name NAME NOT NULL,
    max_interval_per_job BIGINT NOT NULL,
    UNIQUE(user_view_schema, user_view_name),
    UNIQUE(partial_view_schema, partial_view_name)
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.continuous_agg', '');

GRANT SELECT ON _timescaledb_catalog.continuous_agg TO PUBLIC;

CREATE OR REPLACE FUNCTION _timescaledb_internal.finalize_agg_sfunc(
tstate internal, aggfn TEXT, inner_agg_collation_schema NAME, inner_agg_collation_name NAME, inner_agg_input_types NAME[][], inner_agg_serialized_state BYTEA, return_type_dummy_val ANYELEMENT)
RETURNS internal
AS '$libdir/timescaledb-1.7.0', 'ts_finalize_agg_sfunc'
LANGUAGE C IMMUTABLE ;

CREATE OR REPLACE FUNCTION _timescaledb_internal.finalize_agg_ffunc(
tstate internal, aggfn TEXT, inner_agg_collation_schema NAME, inner_agg_collation_name NAME, inner_agg_input_types NAME[][], inner_agg_serialized_state BYTEA, return_type_dummy_val ANYELEMENT)
RETURNS anyelement
AS '$libdir/timescaledb-1.7.0', 'ts_finalize_agg_ffunc'
LANGUAGE C IMMUTABLE ;

CREATE AGGREGATE _timescaledb_internal.finalize_agg(agg_name TEXT,  inner_agg_collation_schema NAME,  inner_agg_collation_name NAME, inner_agg_input_types NAME[][], inner_agg_serialized_state BYTEA, return_type_dummy_val anyelement) (
    SFUNC = _timescaledb_internal.finalize_agg_sfunc,
    STYPE = internal,
    FINALFUNC = _timescaledb_internal.finalize_agg_ffunc,
    FINALFUNC_EXTRA
);

ALTER TABLE _timescaledb_catalog.installation_metadata RENAME TO telemetry_metadata;
ALTER INDEX _timescaledb_catalog.installation_metadata_pkey RENAME TO telemetry_metadata_pkey;

CREATE TABLE IF NOT EXISTS _timescaledb_catalog.continuous_aggs_invalidation_threshold(
    hypertable_id INTEGER PRIMARY KEY REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
    watermark BIGINT NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.continuous_aggs_invalidation_threshold', '');

GRANT SELECT ON _timescaledb_catalog.continuous_aggs_invalidation_threshold TO PUBLIC;

CREATE TABLE IF NOT EXISTS _timescaledb_catalog.continuous_aggs_completed_threshold(
    materialization_id INTEGER PRIMARY KEY
        REFERENCES _timescaledb_catalog.continuous_agg(mat_hypertable_id)
        ON DELETE CASCADE,
    watermark BIGINT NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.continuous_aggs_completed_threshold', '');

GRANT SELECT ON _timescaledb_catalog.continuous_aggs_completed_threshold TO PUBLIC;

-- this does not have an FK on the materialization table since INSERTs to this
-- table are performance critical
CREATE TABLE IF NOT EXISTS _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log(
    hypertable_id INTEGER NOT NULL,
    lowest_modified_value BIGINT NOT NULL,
    greatest_modified_value BIGINT NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.continuous_aggs_hypertable_invalidation_log', '');

CREATE INDEX continuous_aggs_hypertable_invalidation_log_idx
    ON _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log (hypertable_id, lowest_modified_value ASC);

GRANT SELECT ON _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log TO PUBLIC;

DROP FUNCTION IF EXISTS drop_chunks(
    older_than "any",
    table_name  NAME,
    schema_name NAME,
    cascade  BOOLEAN,
    newer_than "any",
    verbose BOOLEAN
);

CREATE OR REPLACE FUNCTION drop_chunks(
    older_than "any" = NULL,
    table_name  NAME = NULL,
    schema_name NAME = NULL,
    cascade  BOOLEAN = FALSE,
    newer_than "any" = NULL,
    verbose BOOLEAN = FALSE,
    cascade_to_materializations BOOLEAN = NULL
) RETURNS SETOF REGCLASS AS '$libdir/timescaledb-1.7.0', 'ts_chunk_drop_chunks'
LANGUAGE C STABLE PARALLEL SAFE;

ALTER TABLE  _timescaledb_config.bgw_job
DROP CONSTRAINT valid_job_type,
ADD CONSTRAINT valid_job_type CHECK (job_type IN ('telemetry_and_version_check_if_enabled', 'reorder', 'drop_chunks', 'continuous_aggregate'));

ALTER TABLE _timescaledb_config.bgw_policy_drop_chunks
  ADD COLUMN cascade_to_materializations BOOLEAN;
DROP FUNCTION IF EXISTS add_drop_chunks_policy(REGCLASS, INTERVAL, BOOL, BOOL);
CREATE OR REPLACE FUNCTION add_drop_chunks_policy(hypertable REGCLASS, older_than INTERVAL, cascade BOOL = FALSE, if_not_exists BOOL = false, cascade_to_materializations BOOL = false)
RETURNS INTEGER
AS '$libdir/timescaledb-1.7.0', 'ts_add_drop_chunks_policy'
LANGUAGE C VOLATILE STRICT;
DROP FUNCTION IF EXISTS _timescaledb_internal.dimension_calculate_default_range_open(bigint, bigint);
DROP FUNCTION IF EXISTS _timescaledb_internal.dimension_calculate_default_range_closed(bigint, smallint);

ALTER TABLE _timescaledb_catalog.telemetry_metadata ADD COLUMN include_in_telemetry BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE _timescaledb_catalog.telemetry_metadata ALTER COLUMN include_in_telemetry DROP DEFAULT;
ALTER TABLE _timescaledb_catalog.telemetry_metadata RENAME TO metadata;
ALTER INDEX _timescaledb_catalog.telemetry_metadata_pkey RENAME TO metadata_pkey;
CREATE TABLE IF NOT EXISTS _timescaledb_catalog.continuous_aggs_materialization_invalidation_log(
    materialization_id INTEGER
        REFERENCES _timescaledb_catalog.continuous_agg(mat_hypertable_id)
        ON DELETE CASCADE,
    lowest_modified_value BIGINT NOT NULL,
    greatest_modified_value BIGINT NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.continuous_aggs_materialization_invalidation_log', '');

CREATE INDEX continuous_aggs_materialization_invalidation_log_idx
    ON _timescaledb_catalog.continuous_aggs_materialization_invalidation_log (materialization_id, lowest_modified_value ASC);

GRANT SELECT ON _timescaledb_catalog.continuous_aggs_materialization_invalidation_log TO PUBLIC;
DROP FUNCTION IF EXISTS get_telemetry_report();

DROP VIEW IF EXISTS timescaledb_information.continuous_aggregate_stats;
DROP FUNCTION IF EXISTS drop_chunks("any",name,name,boolean,"any",boolean,boolean);
DROP FUNCTION IF EXISTS add_drop_chunks_policy(REGCLASS,INTERVAL,BOOL,BOOL,BOOL);

ALTER TABLE _timescaledb_catalog.dimension
ADD COLUMN integer_now_func_schema     NAME     NULL;

ALTER TABLE _timescaledb_catalog.dimension
ADD COLUMN integer_now_func            NAME     NULL;

ALTER TABLE _timescaledb_catalog.dimension
ADD CONSTRAINT dimension_check2
CHECK (
        (integer_now_func_schema IS NULL AND integer_now_func IS NULL) OR
        (integer_now_func_schema IS NOT NULL AND integer_now_func IS NOT NULL)
);
-- ----------------------
CREATE TYPE _timescaledb_catalog.ts_interval AS (
    is_time_interval        BOOLEAN,
    time_interval		    INTERVAL,
    integer_interval        BIGINT
    );

-- q -- todo:: this is probably necessary if we keep the validation constraint in the table definition.
CREATE OR REPLACE FUNCTION _timescaledb_internal.valid_ts_interval(invl _timescaledb_catalog.ts_interval)
RETURNS BOOLEAN AS '$libdir/timescaledb-1.7.0', 'ts_valid_ts_interval' LANGUAGE C VOLATILE STRICT;

DROP VIEW IF EXISTS timescaledb_information.drop_chunks_policies;
DROP VIEW IF EXISTS timescaledb_information.policy_stats;

CREATE TABLE IF NOT EXISTS _timescaledb_config.bgw_policy_drop_chunks_tmp (
    job_id          		    INTEGER                 PRIMARY KEY REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
    hypertable_id   		    INTEGER     UNIQUE      NOT NULL REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
    older_than	    _timescaledb_catalog.ts_interval    NOT NULL,
	cascade					    BOOLEAN                 NOT NULL,
    cascade_to_materializations BOOLEAN                 NOT NULL,
    CONSTRAINT valid_older_than CHECK(_timescaledb_internal.valid_ts_interval(older_than))
);

INSERT INTO _timescaledb_config.bgw_policy_drop_chunks_tmp
(SELECT job_id, hypertable_id, ROW('t',older_than,NULL)::_timescaledb_catalog.ts_interval  as older_than, cascade, cascade_to_materializations
FROM _timescaledb_config.bgw_policy_drop_chunks);

ALTER EXTENSION timescaledb DROP TABLE _timescaledb_config.bgw_policy_drop_chunks;
DROP TABLE _timescaledb_config.bgw_policy_drop_chunks;

CREATE TABLE IF NOT EXISTS _timescaledb_config.bgw_policy_drop_chunks (
    job_id          		    INTEGER                 PRIMARY KEY REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
    hypertable_id   		    INTEGER     UNIQUE      NOT NULL REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
    older_than	    _timescaledb_catalog.ts_interval    NOT NULL,
	cascade					    BOOLEAN                 NOT NULL,
    cascade_to_materializations BOOLEAN                 NOT NULL,
    CONSTRAINT valid_older_than CHECK(_timescaledb_internal.valid_ts_interval(older_than))
);

INSERT INTO _timescaledb_config.bgw_policy_drop_chunks
(SELECT * FROM _timescaledb_config.bgw_policy_drop_chunks_tmp);

SELECT pg_catalog.pg_extension_config_dump('_timescaledb_config.bgw_policy_drop_chunks', '');
DROP TABLE _timescaledb_config.bgw_policy_drop_chunks_tmp;
GRANT SELECT ON _timescaledb_config.bgw_policy_drop_chunks TO PUBLIC;

DROP FUNCTION IF EXISTS alter_job_schedule(INTEGER, INTERVAL, INTERVAL, INTEGER, INTERVAL, BOOL);


--ADDS last_successful_finish column
--Must remove from extension first
ALTER EXTENSION timescaledb DROP TABLE _timescaledb_internal.bgw_job_stat;
DROP VIEW IF EXISTS timescaledb_information.policy_stats;
DROP VIEW IF EXISTS timescaledb_information.continuous_aggregate_stats;

--create table and drop instead of rename so that all indexes dropped as well
CREATE TABLE _timescaledb_internal.bgw_job_stat_tmp AS SELECT * FROM _timescaledb_internal.bgw_job_stat;
DROP TABLE _timescaledb_internal.bgw_job_stat;

CREATE TABLE IF NOT EXISTS _timescaledb_internal.bgw_job_stat (
    job_id                  INTEGER         PRIMARY KEY REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
    last_start              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_finish             TIMESTAMPTZ NOT NULL,
    next_start              TIMESTAMPTZ NOT NULL,
    last_successful_finish  TIMESTAMPTZ NOT NULL,
    last_run_success        BOOL        NOT NULL,
    total_runs              BIGINT      NOT NULL,
    total_duration          INTERVAL    NOT NULL,
    total_successes         BIGINT      NOT NULL,
    total_failures          BIGINT      NOT NULL,
    total_crashes           BIGINT      NOT NULL,
    consecutive_failures    INT         NOT NULL,
    consecutive_crashes     INT         NOT NULL
);
--The job_stat table is not dumped by pg_dump on purpose because (see tables.sql for details)

INSERT INTO _timescaledb_internal.bgw_job_stat
    SELECT job_id,
        last_start,
        last_finish,
        next_start,
        CASE WHEN last_run_success THEN last_finish ELSE '-infinity'::timestamptz END as last_successful_finish,
        last_run_success,
        total_runs,
        total_duration,
        total_successes,
        total_failures,
        total_crashes,
        consecutive_failures,
        consecutive_crashes
    FROM _timescaledb_internal.bgw_job_stat_tmp;

DROP TABLE _timescaledb_internal.bgw_job_stat_tmp;
GRANT SELECT ON _timescaledb_internal.bgw_job_stat TO PUBLIC;





ALTER TABLE _timescaledb_catalog.hypertable add column compressed boolean NOT NULL default false;
ALTER TABLE _timescaledb_catalog.hypertable add column compressed_hypertable_id          INTEGER   REFERENCES _timescaledb_catalog.hypertable(id);
ALTER TABLE _timescaledb_catalog.hypertable drop constraint hypertable_num_dimensions_check;
ALTER TABLE _timescaledb_catalog.hypertable add constraint hypertable_dim_compress_check check ( num_dimensions > 0  or compressed = true );
alter table _timescaledb_catalog.hypertable add constraint hypertable_compress_check check ( compressed = false or (compressed = true and compressed_hypertable_id is null ));

ALTER TABLE _timescaledb_catalog.chunk add column compressed_chunk_id integer references _timescaledb_catalog.chunk(id);
CREATE INDEX IF NOT EXISTS chunk_compressed_chunk_id_idx
ON _timescaledb_catalog.chunk(compressed_chunk_id);

CREATE TABLE _timescaledb_catalog.compression_algorithm(
	id SMALLINT PRIMARY KEY,
	version SMALLINT NOT NULL,
	name NAME NOT NULL,
	description TEXT
);

CREATE TABLE IF NOT EXISTS _timescaledb_catalog.hypertable_compression (
	hypertable_id INTEGER REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
	attname NAME NOT NULL,
	compression_algorithm_id SMALLINT REFERENCES _timescaledb_catalog.compression_algorithm(id),
    segmentby_column_index SMALLINT ,
    orderby_column_index SMALLINT,
    orderby_asc BOOLEAN,
    orderby_nullsfirst BOOLEAN,
	PRIMARY KEY (hypertable_id, attname),
    UNIQUE (hypertable_id, segmentby_column_index),
    UNIQUE (hypertable_id, orderby_column_index)
);

SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.hypertable_compression', '');

CREATE TABLE IF NOT EXISTS _timescaledb_catalog.compression_chunk_size (

    chunk_id            INTEGER REFERENCES _timescaledb_catalog.chunk(id) ON DELETE CASCADE,
    compressed_chunk_id   INTEGER REFERENCES _timescaledb_catalog.chunk(id) ON DELETE CASCADE,
    uncompressed_heap_size BIGINT NOT NULL,
    uncompressed_toast_size BIGINT NOT NULL,
    uncompressed_index_size BIGINT NOT NULL,
    compressed_heap_size BIGINT NOT NULL,
    compressed_toast_size BIGINT NOT NULL,
    compressed_index_size BIGINT NOT NULL,
    PRIMARY KEY( chunk_id, compressed_chunk_id)
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.compression_chunk_size', '');

CREATE TABLE IF NOT EXISTS _timescaledb_config.bgw_policy_compress_chunks(
    job_id                      INTEGER                 PRIMARY KEY REFERENCES _timescaledb_config.bgw_job(id) ON DELETE CASCADE,
    hypertable_id               INTEGER     UNIQUE      NOT NULL REFERENCES _timescaledb_catalog.hypertable(id) ON DELETE CASCADE,
    older_than      _timescaledb_catalog.ts_interval    NOT NULL,
    CONSTRAINT valid_older_than CHECK(_timescaledb_internal.valid_ts_interval(older_than))
);

SELECT pg_catalog.pg_extension_config_dump('_timescaledb_config.bgw_policy_compress_chunks', '');

GRANT SELECT ON _timescaledb_catalog.compression_algorithm TO PUBLIC;
GRANT SELECT ON _timescaledb_catalog.hypertable_compression TO PUBLIC;
GRANT SELECT ON _timescaledb_catalog.compression_chunk_size TO PUBLIC;
GRANT SELECT ON _timescaledb_config.bgw_policy_compress_chunks TO PUBLIC;

CREATE TYPE _timescaledb_internal.compressed_data;

--the textual input/output is simply base64 encoding of the binary representation
CREATE FUNCTION _timescaledb_internal.compressed_data_in(CSTRING)
   RETURNS _timescaledb_internal.compressed_data
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_in'
   LANGUAGE C IMMUTABLE STRICT;

CREATE FUNCTION _timescaledb_internal.compressed_data_out(_timescaledb_internal.compressed_data)
   RETURNS CSTRING
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_out'
   LANGUAGE C IMMUTABLE STRICT;

CREATE FUNCTION _timescaledb_internal.compressed_data_send(_timescaledb_internal.compressed_data)
   RETURNS BYTEA
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_send'
   LANGUAGE C IMMUTABLE STRICT;

CREATE FUNCTION _timescaledb_internal.compressed_data_recv(internal)
   RETURNS _timescaledb_internal.compressed_data
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_recv'
   LANGUAGE C IMMUTABLE STRICT;

CREATE TYPE _timescaledb_internal.compressed_data (
    INTERNALLENGTH = VARIABLE,
    STORAGE = EXTERNAL,
    ALIGNMENT = DOUBLE, --needed for alignment in ARRAY type compression
    INPUT = _timescaledb_internal.compressed_data_in,
    OUTPUT = _timescaledb_internal.compressed_data_out,
    RECEIVE = _timescaledb_internal.compressed_data_recv,
    SEND = _timescaledb_internal.compressed_data_send
);

--insert data for compression_algorithm --
insert into _timescaledb_catalog.compression_algorithm values
( 0, 1, 'COMPRESSION_ALGORITHM_NONE', 'no compression'),
( 1, 1, 'COMPRESSION_ALGORITHM_ARRAY', 'array'),
( 2, 1, 'COMPRESSION_ALGORITHM_DICTIONARY', 'dictionary'),
( 3, 1, 'COMPRESSION_ALGORITHM_GORILLA', 'gorilla'),
( 4, 1, 'COMPRESSION_ALGORITHM_DELTADELTA', 'deltadelta')
on conflict(id) do update set (version, name, description)
= (excluded.version, excluded.name, excluded.description);

--NOTE: below added after initial tagging and release; not
--present in all released versions -- this is also re-executed
--in the next update.
CLUSTER  _timescaledb_catalog.hypertable USING hypertable_pkey;
ALTER TABLE _timescaledb_catalog.hypertable SET WITHOUT CLUSTER;
--rewrite hypertable catalog table because previous updates messed up
--and the table is now using the missingval optimization which doesnt work
--with catalog scans; Note this is equivalent to a VACUUM FULL
--but that command cannot be used inside an update script.
CLUSTER  _timescaledb_catalog.hypertable USING hypertable_pkey;
ALTER TABLE _timescaledb_catalog.hypertable SET WITHOUT CLUSTER;

--The metadata table also has the missingval optimization;
CLUSTER  _timescaledb_catalog.metadata USING metadata_pkey;
ALTER TABLE _timescaledb_catalog.metadata SET WITHOUT CLUSTER;
DO
$BODY$
DECLARE
    hypertable_name TEXT;
BEGIN
    SELECT first_dim.schema_name || '.' || first_dim.table_name
    FROM _timescaledb_catalog.continuous_agg ca
    INNER JOIN LATERAL (
        SELECT dim.*, h.*
        FROM _timescaledb_catalog.hypertable h
        INNER JOIN _timescaledb_catalog.dimension dim ON (dim.hypertable_id = h.id)
        WHERE ca.raw_hypertable_id = h.id
        ORDER by dim.id ASC
        LIMIT 1
    ) first_dim ON true
    WHERE first_dim.column_type IN (REGTYPE 'int2', REGTYPE 'int4', REGTYPE 'int8')
    AND (first_dim.integer_now_func_schema IS NULL OR first_dim.integer_now_func IS NULL)
    INTO hypertable_name;

    IF hypertable_name is not null AND (current_setting('timescaledb.ignore_update_errors', true) is null OR current_setting('timescaledb.ignore_update_errors', true) != 'on') THEN
        RAISE 'The continuous aggregate on hypertable "%" will break unless an integer_now func is set using set_integer_now_func().', hypertable_name;
    END IF;
END
$BODY$;


ALTER TABLE  _timescaledb_catalog.continuous_agg
    ADD COLUMN  ignore_invalidation_older_than BIGINT NOT NULL DEFAULT BIGINT '9223372036854775807';
UPDATE _timescaledb_catalog.continuous_agg SET ignore_invalidation_older_than = BIGINT '9223372036854775807';

CLUSTER  _timescaledb_catalog.continuous_agg USING continuous_agg_pkey;
ALTER TABLE _timescaledb_catalog.continuous_agg SET WITHOUT CLUSTER;

CREATE INDEX IF NOT EXISTS continuous_agg_raw_hypertable_id_idx
      ON _timescaledb_catalog.continuous_agg(raw_hypertable_id);


--Add modification_time column
CREATE TABLE _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log_tmp AS SELECT * FROM _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log;
ALTER EXTENSION timescaledb DROP TABLE _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log;
DROP TABLE _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log;
CREATE TABLE IF NOT EXISTS _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log
(
    hypertable_id              INTEGER NOT NULL,
    modification_time BIGINT  NOT NULL, --time at which the raw table was modified
    lowest_modified_value      BIGINT  NOT NULL,
    greatest_modified_value    BIGINT  NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.continuous_aggs_hypertable_invalidation_log', '');
--modification_time == INT_MIN to cause these invalidations to be processed
INSERT INTO _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log
    SELECT hypertable_id, BIGINT '-9223372036854775808', lowest_modified_value, greatest_modified_value
    FROM _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log_tmp;
DROP TABLE _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log_tmp;
CREATE INDEX continuous_aggs_hypertable_invalidation_log_idx
    ON _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log (hypertable_id, lowest_modified_value ASC);
GRANT SELECT ON  _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log TO PUBLIC;

--Add modification_time column
CREATE TABLE _timescaledb_catalog.continuous_aggs_materialization_invalidation_log_tmp AS SELECT * FROM _timescaledb_catalog.continuous_aggs_materialization_invalidation_log;
ALTER EXTENSION timescaledb DROP TABLE _timescaledb_catalog.continuous_aggs_materialization_invalidation_log;
DROP TABLE _timescaledb_catalog.continuous_aggs_materialization_invalidation_log;
CREATE TABLE IF NOT EXISTS _timescaledb_catalog.continuous_aggs_materialization_invalidation_log
(
    materialization_id         INTEGER
        REFERENCES _timescaledb_catalog.continuous_agg (mat_hypertable_id)
            ON DELETE CASCADE,
    modification_time BIGINT NOT NULL, --time at which the raw table was modified
    lowest_modified_value      BIGINT NOT NULL,
    greatest_modified_value    BIGINT NOT NULL
);
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_catalog.continuous_aggs_materialization_invalidation_log', '');
--modification_time == INT_MIN to cause these invalidations to be processed
INSERT INTO _timescaledb_catalog.continuous_aggs_materialization_invalidation_log
    SELECT materialization_id, BIGINT '-9223372036854775808', lowest_modified_value, greatest_modified_value
    FROM _timescaledb_catalog.continuous_aggs_materialization_invalidation_log_tmp;
DROP TABLE _timescaledb_catalog.continuous_aggs_materialization_invalidation_log_tmp;
CREATE INDEX continuous_aggs_materialization_invalidation_log_idx
    ON _timescaledb_catalog.continuous_aggs_materialization_invalidation_log (materialization_id, lowest_modified_value ASC);
GRANT SELECT ON  _timescaledb_catalog.continuous_aggs_materialization_invalidation_log TO PUBLIC;

ALTER TABLE _timescaledb_config.bgw_policy_drop_chunks ALTER COLUMN cascade_to_materializations DROP NOT NULL;

UPDATE _timescaledb_config.bgw_policy_drop_chunks SET cascade_to_materializations = NULL WHERE cascade_to_materializations = false;

ALTER TABLE  _timescaledb_catalog.chunk ADD COLUMN dropped BOOLEAN DEFAULT false;
UPDATE _timescaledb_catalog.chunk SET dropped = false;
ALTER TABLE _timescaledb_catalog.chunk ALTER COLUMN dropped SET NOT NULL;

CLUSTER  _timescaledb_catalog.chunk USING chunk_pkey;
ALTER TABLE _timescaledb_catalog.chunk SET WITHOUT CLUSTER;
DROP VIEW IF EXISTS timescaledb_information.continuous_aggregates;

DROP VIEW IF EXISTS timescaledb_information.continuous_aggregates;

ALTER TABLE IF EXISTS _timescaledb_catalog.continuous_agg ADD COLUMN IF NOT EXISTS  materialized_only BOOL NOT NULL DEFAULT false;

-- all continuous aggregrates created before this update had materialized only views
UPDATE _timescaledb_catalog.continuous_agg SET materialized_only = true;

-- rewrite catalog table to not break catalog scans on tables with missingval optimization
CLUSTER  _timescaledb_catalog.continuous_agg USING continuous_agg_pkey;
ALTER TABLE _timescaledb_catalog.continuous_agg SET WITHOUT CLUSTER;

-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.


-- Functions have to be run in 2 places:
-- 1) In pre-install between types.pre.sql and types.post.sql to set up the types.
-- 2) On every update to make sure the function points to the correct versioned.so


-- PostgreSQL composite types do not support constraint checks. That is why any table having a ts_interval column must use the following
-- function for constraint validation.
-- This function needs to be defined before executing pre_install/tables.sql because it is used as
-- validation constraint for columns of type ts_interval.
CREATE OR REPLACE FUNCTION _timescaledb_internal.valid_ts_interval(invl _timescaledb_catalog.ts_interval)
RETURNS BOOLEAN AS '$libdir/timescaledb-1.7.0', 'ts_valid_ts_interval' LANGUAGE C VOLATILE STRICT;

--the textual input/output is simply base64 encoding of the binary representation
CREATE OR REPLACE FUNCTION _timescaledb_internal.compressed_data_in(CSTRING)
   RETURNS _timescaledb_internal.compressed_data
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_in'
   LANGUAGE C IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION _timescaledb_internal.compressed_data_out(_timescaledb_internal.compressed_data)
   RETURNS CSTRING
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_out'
   LANGUAGE C IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION _timescaledb_internal.compressed_data_send(_timescaledb_internal.compressed_data)
   RETURNS BYTEA
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_send'
   LANGUAGE C IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION _timescaledb_internal.compressed_data_recv(internal)
   RETURNS _timescaledb_internal.compressed_data
   AS '$libdir/timescaledb-1.7.0', 'ts_compressed_data_recv'
   LANGUAGE C IMMUTABLE STRICT;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- Trigger that blocks INSERTs on the hypertable's root table
CREATE OR REPLACE FUNCTION _timescaledb_internal.insert_blocker() RETURNS trigger
AS '$libdir/timescaledb-1.7.0', 'ts_hypertable_insert_blocker' LANGUAGE C;

-- Records mutations or INSERTs which would invalidate a continuous aggregate
CREATE OR REPLACE FUNCTION _timescaledb_internal.continuous_agg_invalidation_trigger() RETURNS TRIGGER
AS '$libdir/timescaledb-1.7.0', 'ts_continuous_agg_invalidation_trigger' LANGUAGE C;

CREATE OR REPLACE FUNCTION set_integer_now_func(hypertable REGCLASS, integer_now_func REGPROC, replace_if_exists BOOL = false) RETURNS VOID
AS '$libdir/timescaledb-1.7.0', 'ts_hypertable_set_integer_now_func'
LANGUAGE C VOLATILE STRICT;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- Built-in function for calculating the next chunk interval when
-- using adaptive chunking. The function can be replaced by a
-- user-defined function with the same signature.
--
-- The parameters passed to the function are as follows:
--
-- dimension_id: the ID of the dimension to calculate the interval for
-- dimension_coord: the coordinate / point on the dimensional axis
-- where the tuple that triggered this chunk creation falls.
-- chunk_target_size: the target size in bytes that the chunk should have.
--
-- The function should return the new interval in dimension-specific
-- time (ususally microseconds).
CREATE OR REPLACE FUNCTION _timescaledb_internal.calculate_chunk_interval(
        dimension_id INTEGER,
        dimension_coord BIGINT,
        chunk_target_size BIGINT
) RETURNS BIGINT AS '$libdir/timescaledb-1.7.0', 'ts_calculate_chunk_interval' LANGUAGE C;

-- Function for explicit chunk exclusion. Supply a record and an array
-- of chunk ids as input.
-- Intended to be used in WHERE clause.
-- An example: SELECT * FROM hypertable WHERE _timescaledb_internal.chunks_in(hypertable, ARRAY[1,2]);
--
-- Use it with care as this function directly affects what chunks are being scanned for data.
-- Although this function is immutable (always returns true), we declare it here as volatile
-- so that the PostgreSQL optimizer does not try to evaluate/reduce it in the planner phase
CREATE OR REPLACE FUNCTION _timescaledb_internal.chunks_in(record RECORD, chunks INTEGER[]) RETURNS BOOL
AS '$libdir/timescaledb-1.7.0', 'ts_chunks_in' LANGUAGE C VOLATILE STRICT;

--given a chunk's relid, return the id. Error out if not a chunk relid.
CREATE OR REPLACE FUNCTION _timescaledb_internal.chunk_id_from_relid(relid OID) RETURNS INTEGER
AS '$libdir/timescaledb-1.7.0', 'ts_chunk_id_from_relid' LANGUAGE C STABLE STRICT PARALLEL SAFE;

--trigger to block dml on a chunk --
CREATE OR REPLACE FUNCTION _timescaledb_internal.chunk_dml_blocker() RETURNS trigger
AS '$libdir/timescaledb-1.7.0', 'ts_chunk_dml_blocker' LANGUAGE C;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

--documentation of these function located in chunk_index.h
CREATE OR REPLACE FUNCTION _timescaledb_internal.chunk_index_clone(chunk_index_oid OID) RETURNS OID
AS '$libdir/timescaledb-1.7.0', 'ts_chunk_index_clone' LANGUAGE C VOLATILE STRICT;

CREATE OR REPLACE FUNCTION _timescaledb_internal.chunk_index_replace(chunk_index_oid_old OID, chunk_index_oid_new OID) RETURNS VOID
AS '$libdir/timescaledb-1.7.0', 'ts_chunk_index_replace' LANGUAGE C VOLATILE STRICT;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION _timescaledb_internal.enterprise_enabled() RETURNS BOOLEAN
AS '$libdir/timescaledb-1.7.0', 'ts_enterprise_enabled' LANGUAGE C;

CREATE OR REPLACE FUNCTION _timescaledb_internal.current_license_key() RETURNS TEXT
AS '$libdir/timescaledb-1.7.0', 'ts_current_license_key' LANGUAGE C;

CREATE OR REPLACE FUNCTION _timescaledb_internal.tsl_loaded() RETURNS BOOLEAN
AS '$libdir/timescaledb-1.7.0', 'ts_tsl_loaded' LANGUAGE C;

CREATE OR REPLACE FUNCTION _timescaledb_internal.license_expiration_time() RETURNS TIMESTAMPTZ
AS '$libdir/timescaledb-1.7.0', 'ts_license_expiration_time' LANGUAGE C;

CREATE OR REPLACE FUNCTION _timescaledb_internal.print_license_expiration_info() RETURNS VOID
AS '$libdir/timescaledb-1.7.0', 'ts_print_tsl_license_expiration_info' LANGUAGE C;

CREATE OR REPLACE FUNCTION _timescaledb_internal.license_edition() RETURNS TEXT
AS '$libdir/timescaledb-1.7.0', 'ts_license_edition' LANGUAGE C;

CREATE OR REPLACE FUNCTION _timescaledb_internal.current_db_set_license_key(new_key TEXT) RETURNS TEXT AS 
$BODY$
DECLARE 
    db text; 
BEGIN
    SELECT current_database() INTO db;
    EXECUTE format('ALTER DATABASE %I SET timescaledb.license_key = %L', db, new_key);
    EXECUTE format('SET SESSION timescaledb.license_key = %L', new_key);
    PERFORM _timescaledb_internal.restart_background_workers();
    RETURN new_key;
END
$BODY$ 
LANGUAGE PLPGSQL;


-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- This file contains utilities for time conversion.
CREATE OR REPLACE FUNCTION _timescaledb_internal.to_unix_microseconds(ts TIMESTAMPTZ) RETURNS BIGINT
    AS '$libdir/timescaledb-1.7.0', 'ts_pg_timestamp_to_unix_microseconds' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.to_timestamp(unixtime_us BIGINT) RETURNS TIMESTAMPTZ
    AS '$libdir/timescaledb-1.7.0', 'ts_pg_unix_microseconds_to_timestamp' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.to_timestamp_without_timezone(unixtime_us BIGINT)
  RETURNS TIMESTAMP
  AS '$libdir/timescaledb-1.7.0', 'ts_pg_unix_microseconds_to_timestamp'
  LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.to_date(unixtime_us BIGINT)
  RETURNS DATE
  AS '$libdir/timescaledb-1.7.0', 'ts_pg_unix_microseconds_to_date'
  LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.to_interval(unixtime_us BIGINT) RETURNS INTERVAL
    AS '$libdir/timescaledb-1.7.0', 'ts_pg_unix_microseconds_to_interval' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

-- Time can be represented in a hypertable as an int* (bigint/integer/smallint) or as a timestamp type (
-- with or without timezones). In metatables and other internal systems all time values are stored as bigint.
-- Converting from int* columns to internal representation is a cast to bigint.
-- Converting from timestamps to internal representation is conversion to epoch (in microseconds).

-- Gets the sql code for representing the literal for the given time value (in the internal representation) as the column_type.
CREATE OR REPLACE FUNCTION _timescaledb_internal.time_literal_sql(
    time_value      BIGINT,
    column_type     REGTYPE
)
    RETURNS text LANGUAGE PLPGSQL STABLE AS
$BODY$
DECLARE
    ret text;
BEGIN
    IF time_value IS NULL THEN
        RETURN format('%L', NULL);
    END IF;
    CASE column_type
      WHEN 'BIGINT'::regtype, 'INTEGER'::regtype, 'SMALLINT'::regtype THEN
        RETURN format('%L', time_value); -- scale determined by user.
      WHEN 'TIMESTAMP'::regtype THEN
        --the time_value for timestamps w/o tz does not depend on local timezones. So perform at UTC.
        RETURN format('TIMESTAMP %1$L', timezone('UTC',_timescaledb_internal.to_timestamp(time_value))); -- microseconds
      WHEN 'TIMESTAMPTZ'::regtype THEN
        -- assume time_value is in microsec
        RETURN format('TIMESTAMPTZ %1$L', _timescaledb_internal.to_timestamp(time_value)); -- microseconds
      WHEN 'DATE'::regtype THEN
        RETURN format('%L', timezone('UTC',_timescaledb_internal.to_timestamp(time_value))::date);
      ELSE
         EXECUTE 'SELECT format(''%L'', $1::' || column_type::text || ')' into ret using time_value;
         RETURN ret;
    END CASE;
END
$BODY$;

CREATE OR REPLACE FUNCTION _timescaledb_internal.interval_to_usec(
       chunk_interval INTERVAL
)
RETURNS BIGINT LANGUAGE SQL IMMUTABLE PARALLEL SAFE AS
$BODY$
    SELECT (int_sec * 1000000)::bigint from extract(epoch from chunk_interval) as int_sec;
$BODY$;

CREATE OR REPLACE FUNCTION _timescaledb_internal.time_to_internal(time_val ANYELEMENT)
RETURNS BIGINT AS '$libdir/timescaledb-1.7.0', 'ts_time_to_internal' LANGUAGE C VOLATILE STRICT;

-- return the materialization watermark for a continuous aggregate materialization hypertable
-- returns NULL when no materialization has happened yet
CREATE OR REPLACE FUNCTION _timescaledb_internal.cagg_watermark(hypertable_id oid)
RETURNS INT8 LANGUAGE SQL AS
$BODY$

  SELECT
    watermark
  FROM
    _timescaledb_catalog.continuous_agg cagg
    LEFT JOIN _timescaledb_catalog.continuous_aggs_completed_threshold completed ON completed.materialization_id = cagg.mat_hypertable_id
  WHERE
    cagg.raw_hypertable_id = $1;

$BODY$ STABLE STRICT;

-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- This file contains functions associated with creating new
-- hypertables.

CREATE OR REPLACE FUNCTION _timescaledb_internal.dimension_is_finite(
    val      BIGINT
)
    RETURNS BOOLEAN LANGUAGE SQL IMMUTABLE PARALLEL SAFE AS
$BODY$
    --end values of bigint reserved for infinite
    SELECT val > (-9223372036854775808)::bigint AND val < 9223372036854775807::bigint
$BODY$;


CREATE OR REPLACE FUNCTION _timescaledb_internal.dimension_slice_get_constraint_sql(
    dimension_slice_id  INTEGER
)
    RETURNS TEXT LANGUAGE PLPGSQL VOLATILE AS
$BODY$
DECLARE
    dimension_slice_row _timescaledb_catalog.dimension_slice;
    dimension_row _timescaledb_catalog.dimension;
    dimension_def TEXT;
    dimtype REGTYPE;
    parts TEXT[];
BEGIN
    SELECT * INTO STRICT dimension_slice_row
    FROM _timescaledb_catalog.dimension_slice
    WHERE id = dimension_slice_id;

    SELECT * INTO STRICT dimension_row
    FROM _timescaledb_catalog.dimension
    WHERE id = dimension_slice_row.dimension_id;

    IF dimension_row.partitioning_func_schema IS NOT NULL AND
       dimension_row.partitioning_func IS NOT NULL THEN
        SELECT prorettype INTO STRICT dimtype
        FROM pg_catalog.pg_proc pro
        WHERE pro.oid = format('%I.%I', dimension_row.partitioning_func_schema, dimension_row.partitioning_func)::regproc::oid;

        dimension_def := format('%1$I.%2$I(%3$I)',
             dimension_row.partitioning_func_schema,
             dimension_row.partitioning_func,
             dimension_row.column_name);
    ELSE
        dimension_def := format('%1$I', dimension_row.column_name);
        dimtype := dimension_row.column_type;
    END IF;

    IF dimension_row.num_slices IS NOT NULL THEN

        IF  _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_start) THEN
            parts = parts || format(' %1$s >= %2$L ', dimension_def, dimension_slice_row.range_start);
        END IF;

        IF _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_end) THEN
            parts = parts || format(' %1$s < %2$L ', dimension_def, dimension_slice_row.range_end);
        END IF;

        IF array_length(parts, 1) = 0 THEN
            RETURN NULL;
        END IF;
        return array_to_string(parts, 'AND');
    ELSE
        --TODO: only works with time for now
        IF _timescaledb_internal.time_literal_sql(dimension_slice_row.range_start, dimtype) =
           _timescaledb_internal.time_literal_sql(dimension_slice_row.range_end, dimtype) THEN
            RAISE 'time-based constraints have the same start and end values for column "%": %',
                    dimension_row.column_name,
                    _timescaledb_internal.time_literal_sql(dimension_slice_row.range_end, dimtype);
        END IF;

        parts = ARRAY[]::text[];

        IF _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_start) THEN
            parts = parts || format(' %1$s >= %2$s ',
            dimension_def,
            _timescaledb_internal.time_literal_sql(dimension_slice_row.range_start, dimtype));
        END IF;

        IF _timescaledb_internal.dimension_is_finite(dimension_slice_row.range_end) THEN
            parts = parts || format(' %1$s < %2$s ',
            dimension_def,
            _timescaledb_internal.time_literal_sql(dimension_slice_row.range_end, dimtype));
        END IF;

        return array_to_string(parts, 'AND');
    END IF;
END
$BODY$;

-- Outputs the create_hypertable command to recreate the given hypertable.
--
-- This is currently used internally for our single hypertable backup tool
-- so that it knows how to restore the hypertable without user intervention.
--
-- It only works for hypertables with up to 2 dimensions.
CREATE OR REPLACE FUNCTION _timescaledb_internal.get_create_command(
    table_name NAME
)
    RETURNS TEXT LANGUAGE PLPGSQL VOLATILE AS
$BODY$
DECLARE
    h_id             INTEGER;
    schema_name      NAME;
    time_column      NAME;
    time_interval    BIGINT;
    space_column     NAME;
    space_partitions INTEGER;
    dimension_cnt    INTEGER;
    dimension_row    record;
    ret              TEXT;
BEGIN
    SELECT h.id, h.schema_name
    FROM _timescaledb_catalog.hypertable AS h
    WHERE h.table_name = get_create_command.table_name
    INTO h_id, schema_name;

    IF h_id IS NULL THEN
        RAISE EXCEPTION 'hypertable "%" not found', table_name
        USING ERRCODE = 'TS101';
    END IF;

    SELECT COUNT(*)
    FROM _timescaledb_catalog.dimension d
    WHERE d.hypertable_id = h_id
    INTO STRICT dimension_cnt;

    IF dimension_cnt > 2 THEN
        RAISE EXCEPTION 'get_create_command only supports hypertables with up to 2 dimensions'
        USING ERRCODE = 'TS101';
    END IF;

    FOR dimension_row IN
        SELECT *
        FROM _timescaledb_catalog.dimension d
        WHERE d.hypertable_id = h_id
        LOOP
        IF dimension_row.interval_length IS NOT NULL THEN
            time_column := dimension_row.column_name;
            time_interval := dimension_row.interval_length;
        ELSIF dimension_row.num_slices IS NOT NULL THEN
            space_column := dimension_row.column_name;
            space_partitions := dimension_row.num_slices;
        END IF;
    END LOOP;

    ret := format($$SELECT create_hypertable('%I.%I', '%s'$$, schema_name, table_name, time_column);
    IF space_column IS NOT NULL THEN
        ret := ret || format($$, '%I', %s$$, space_column, space_partitions);
    END IF;
    ret := ret || format($$, chunk_time_interval => %s, create_default_indexes=>FALSE);$$, time_interval);

    RETURN ret;
END
$BODY$;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- Creates a constraint on a chunk.
CREATE OR REPLACE FUNCTION _timescaledb_internal.chunk_constraint_add_table_constraint(
    chunk_constraint_row  _timescaledb_catalog.chunk_constraint
)
    RETURNS VOID LANGUAGE PLPGSQL AS
$BODY$
DECLARE
    chunk_row _timescaledb_catalog.chunk;
    hypertable_row _timescaledb_catalog.hypertable;
    constraint_oid OID;
    check_sql TEXT;
    def TEXT;
BEGIN
    SELECT * INTO STRICT chunk_row FROM _timescaledb_catalog.chunk c WHERE c.id = chunk_constraint_row.chunk_id;
    SELECT * INTO STRICT hypertable_row FROM _timescaledb_catalog.hypertable h WHERE h.id = chunk_row.hypertable_id;

    IF chunk_constraint_row.dimension_slice_id IS NOT NULL THEN
        check_sql = _timescaledb_internal.dimension_slice_get_constraint_sql(chunk_constraint_row.dimension_slice_id);
        IF check_sql IS NOT NULL THEN
            def := format('CHECK (%s)',  check_sql);
        ELSE
            def := NULL;
        END IF;
    ELSIF chunk_constraint_row.hypertable_constraint_name IS NOT NULL THEN
        SELECT oid INTO STRICT constraint_oid FROM pg_constraint
        WHERE conname=chunk_constraint_row.hypertable_constraint_name AND
              conrelid = format('%I.%I', hypertable_row.schema_name, hypertable_row.table_name)::regclass::oid;
        def := pg_get_constraintdef(constraint_oid);
    ELSE
        RAISE 'unknown constraint type';
    END IF;

    IF def IS NOT NULL THEN
        EXECUTE format(
            $$ ALTER TABLE %I.%I ADD CONSTRAINT %I %s $$,
            chunk_row.schema_name, chunk_row.table_name, chunk_constraint_row.constraint_name, def
        );
    END IF;
END
$BODY$;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- Clone fk constraint from a hypertable
CREATE OR REPLACE FUNCTION _timescaledb_internal.hypertable_constraint_add_table_fk_constraint(
    user_ht_constraint_name NAME,
    user_ht_schema_name NAME,
    user_ht_table_name NAME,
    compress_ht_id INTEGER
)
    RETURNS VOID LANGUAGE PLPGSQL AS
$BODY$
DECLARE
    compressed_ht_row _timescaledb_catalog.hypertable;
    constraint_oid OID;
    check_sql TEXT;
    def TEXT;
BEGIN
    SELECT * INTO STRICT compressed_ht_row FROM _timescaledb_catalog.hypertable h
    WHERE h.id = compress_ht_id;
    IF user_ht_constraint_name IS NOT NULL THEN
        SELECT oid INTO STRICT constraint_oid FROM pg_constraint
        WHERE conname=user_ht_constraint_name AND contype = 'f' AND
              conrelid = format('%I.%I', user_ht_schema_name, user_ht_table_name)::regclass::oid;
        def := pg_get_constraintdef(constraint_oid);
    ELSE
        RAISE 'unknown constraint type';
    END IF;
    IF def IS NOT NULL THEN
        EXECUTE format(
            $$ ALTER TABLE %I.%I ADD CONSTRAINT %I %s $$,
            compressed_ht_row.schema_name, compressed_ht_row.table_name, user_ht_constraint_name, def
        );
    END IF;

END
$BODY$;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- Deprecated partition hash function
CREATE OR REPLACE FUNCTION _timescaledb_internal.get_partition_for_key(val anyelement)
    RETURNS int
    AS '$libdir/timescaledb-1.7.0', 'ts_get_partition_for_key' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.get_partition_hash(val anyelement)
    RETURNS int
    AS '$libdir/timescaledb-1.7.0', 'ts_get_partition_hash' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.get_time_type(hypertable_id INTEGER)
    RETURNS OID
    AS '$libdir/timescaledb-1.7.0', 'ts_hypertable_get_time_type' LANGUAGE C STABLE STRICT;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- This file contains functions related to getting information about the
-- schema of a hypertable, including columns, their types, etc.


-- Check if a given table OID is a main table (i.e. the table a user
-- targets for SQL operations) for a hypertable
CREATE OR REPLACE FUNCTION _timescaledb_internal.is_main_table(
    table_oid regclass
)
    RETURNS bool LANGUAGE SQL STABLE AS
$BODY$
    SELECT EXISTS(SELECT 1 FROM _timescaledb_catalog.hypertable WHERE table_name = relname AND schema_name = nspname)
    FROM pg_class c
    INNER JOIN pg_namespace n ON (n.OID = c.relnamespace)
    WHERE c.OID = table_oid;
$BODY$;

-- Check if given table is a hypertable's main table
CREATE OR REPLACE FUNCTION _timescaledb_internal.is_main_table(
    schema_name NAME,
    table_name  NAME
)
    RETURNS BOOLEAN LANGUAGE SQL STABLE AS
$BODY$
     SELECT EXISTS(
         SELECT 1 FROM _timescaledb_catalog.hypertable h
         WHERE h.schema_name = is_main_table.schema_name AND 
               h.table_name = is_main_table.table_name
     );
$BODY$;

-- Get a hypertable given its main table OID
CREATE OR REPLACE FUNCTION _timescaledb_internal.hypertable_from_main_table(
    table_oid regclass
)
    RETURNS _timescaledb_catalog.hypertable LANGUAGE SQL STABLE AS
$BODY$
    SELECT h.*
    FROM pg_class c
    INNER JOIN pg_namespace n ON (n.OID = c.relnamespace)
    INNER JOIN _timescaledb_catalog.hypertable h ON (h.table_name = c.relname AND h.schema_name = n.nspname)
    WHERE c.OID = table_oid;
$BODY$;

CREATE OR REPLACE FUNCTION _timescaledb_internal.main_table_from_hypertable(
    hypertable_id int
)
    RETURNS regclass LANGUAGE SQL STABLE AS
$BODY$
    SELECT format('%I.%I',h.schema_name, h.table_name)::regclass
    FROM _timescaledb_catalog.hypertable h
    WHERE id = hypertable_id;
$BODY$;


-- Get the name of the time column for a chunk.
--
-- schema_name, table_name - name of the schema and table for the table represented by the crn.
CREATE OR REPLACE FUNCTION _timescaledb_internal.time_col_name_for_chunk(
    schema_name NAME,
    table_name  NAME
)
    RETURNS NAME LANGUAGE PLPGSQL STABLE AS
$BODY$
DECLARE
    time_col_name NAME;
BEGIN
    SELECT h.time_column_name INTO STRICT time_col_name
    FROM _timescaledb_catalog.hypertable h
    INNER JOIN _timescaledb_catalog.chunk c ON (c.hypertable_id = h.id)
    WHERE c.schema_name = time_col_name_for_chunk.schema_name AND
    c.table_name = time_col_name_for_chunk.table_name;
    RETURN time_col_name;
END
$BODY$;

-- Get the type of the time column for a chunk.
--
-- schema_name, table_name - name of the schema and table for the table represented by the crn.
CREATE OR REPLACE FUNCTION _timescaledb_internal.time_col_type_for_chunk(
    schema_name NAME,
    table_name  NAME
)
    RETURNS REGTYPE LANGUAGE PLPGSQL STABLE AS
$BODY$
DECLARE
    time_col_type REGTYPE;
BEGIN
    SELECT h.time_column_type INTO STRICT time_col_type
    FROM _timescaledb_catalog.hypertable h
    INNER JOIN _timescaledb_catalog.chunk c ON (c.hypertable_id = h.id)
    WHERE c.schema_name = time_col_type_for_chunk.schema_name AND
    c.table_name = time_col_type_for_chunk.table_name;
    RETURN time_col_type;
END
$BODY$;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- This file defines DDL functions for adding and manipulating hypertables.

-- Converts a regular postgres table to a hypertable.
--
-- main_table - The OID of the table to be converted
-- time_column_name - Name of the column that contains time for a given record
-- partitioning_column - Name of the column to partition data by
-- number_partitions - (Optional) Number of partitions for data
-- associated_schema_name - (Optional) Schema for internal hypertable tables
-- associated_table_prefix - (Optional) Prefix for internal hypertable table names
-- chunk_time_interval - (Optional) Initial time interval for a chunk
-- create_default_indexes - (Optional) Whether or not to create the default indexes
-- if_not_exists - (Optional) Do not fail if table is already a hypertable
-- partitioning_func - (Optional) The partitioning function to use for spatial partitioning
-- migrate_data - (Optional) Set to true to migrate any existing data in the table to chunks
-- chunk_target_size - (Optional) The target size for chunks (e.g., '1000MB', 'estimate', or 'off')
-- chunk_sizing_func - (Optional) A function to calculate the chunk time interval for new chunks
-- time_partitioning_func - (Optional) The partitioning function to use for "time" partitioning
CREATE OR REPLACE FUNCTION  create_hypertable(
    main_table              REGCLASS,
    time_column_name        NAME,
    partitioning_column     NAME = NULL,
    number_partitions       INTEGER = NULL,
    associated_schema_name  NAME = NULL,
    associated_table_prefix NAME = NULL,
    chunk_time_interval     ANYELEMENT = NULL::bigint,
    create_default_indexes  BOOLEAN = TRUE,
    if_not_exists           BOOLEAN = FALSE,
    partitioning_func       REGPROC = NULL,
    migrate_data            BOOLEAN = FALSE,
    chunk_target_size       TEXT = NULL,
    chunk_sizing_func       REGPROC = '_timescaledb_internal.calculate_chunk_interval'::regproc,
    time_partitioning_func  REGPROC = NULL
) RETURNS TABLE(hypertable_id INT, schema_name NAME, table_name NAME, created BOOL) AS '$libdir/timescaledb-1.7.0', 'ts_hypertable_create' LANGUAGE C VOLATILE;

-- Set adaptive chunking. To disable, set chunk_target_size => 'off'.
CREATE OR REPLACE FUNCTION  set_adaptive_chunking(
    hypertable                     REGCLASS,
    chunk_target_size              TEXT,
    INOUT chunk_sizing_func        REGPROC = '_timescaledb_internal.calculate_chunk_interval'::regproc,
    OUT chunk_target_size          BIGINT
) RETURNS RECORD AS '$libdir/timescaledb-1.7.0', 'ts_chunk_adaptive_set' LANGUAGE C VOLATILE;

-- Update chunk_time_interval for a hypertable.
--
-- main_table - The OID of the table corresponding to a hypertable whose time
--     interval should be updated
-- chunk_time_interval - The new time interval. For hypertables with integral
--     time columns, this must be an integral type. For hypertables with a
--     TIMESTAMP/TIMESTAMPTZ/DATE type, it can be integral which is treated as
--     microseconds, or an INTERVAL type.
CREATE OR REPLACE FUNCTION  set_chunk_time_interval(
    main_table              REGCLASS,
    chunk_time_interval     ANYELEMENT,
    dimension_name          NAME = NULL
) RETURNS VOID AS '$libdir/timescaledb-1.7.0', 'ts_dimension_set_interval' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION  set_number_partitions(
    main_table              REGCLASS,
    number_partitions       INTEGER,
    dimension_name          NAME = NULL
) RETURNS VOID AS '$libdir/timescaledb-1.7.0', 'ts_dimension_set_num_slices' LANGUAGE C VOLATILE;

-- Drop chunks older than the given timestamp. If a hypertable name is given,
-- drop only chunks associated with this table. Any of the first three arguments
-- can be NULL meaning "all values".
CREATE OR REPLACE FUNCTION drop_chunks(
    older_than "any" = NULL,
    table_name  NAME = NULL,
    schema_name NAME = NULL,
    cascade  BOOLEAN = FALSE,
    newer_than "any" = NULL,
    verbose BOOLEAN = FALSE,
    cascade_to_materializations BOOLEAN = NULL
) RETURNS SETOF TEXT AS '$libdir/timescaledb-1.7.0', 'ts_chunk_drop_chunks'
LANGUAGE C VOLATILE PARALLEL UNSAFE;

-- show chunks older than or newer than a specific time.
-- `hypertable` argument can be a valid hypertable or NULL.
-- In the latter case the function will try to list all
-- the chunks from all of the hypertables in the database.
-- older_than or newer_than or both can be NULL.
-- if `hypertable` argument is null but a time constraint is specified
-- through older_than or newer_than, the call will succeed
-- if and only if all the hypertables in the database
-- have the same type as the given time constraint argument
CREATE OR REPLACE FUNCTION show_chunks(
    hypertable  REGCLASS = NULL,
    older_than "any" = NULL,
    newer_than "any" = NULL
) RETURNS SETOF REGCLASS AS '$libdir/timescaledb-1.7.0', 'ts_chunk_show_chunks'
LANGUAGE C STABLE PARALLEL SAFE;

-- Add a dimension (of partitioning) to a hypertable
--
-- main_table - OID of the table to add a dimension to
-- column_name - NAME of the column to use in partitioning for this dimension
-- number_partitions - Number of partitions, for non-time dimensions
-- interval_length - Size of intervals for time dimensions (can be integral or INTERVAL)
-- partitioning_func - Function used to partition the column
-- if_not_exists - If set, and the dimension already exists, generate a notice instead of an error
CREATE OR REPLACE FUNCTION  add_dimension(
    main_table              REGCLASS,
    column_name             NAME,
    number_partitions       INTEGER = NULL,
    chunk_time_interval     ANYELEMENT = NULL::BIGINT,
    partitioning_func       REGPROC = NULL,
    if_not_exists           BOOLEAN = FALSE
) RETURNS TABLE(dimension_id INT, schema_name NAME, table_name NAME, column_name NAME, created BOOL)
AS '$libdir/timescaledb-1.7.0', 'ts_dimension_add' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION attach_tablespace(
    tablespace NAME,
    hypertable REGCLASS,
    if_not_attached BOOLEAN = false
) RETURNS VOID
AS '$libdir/timescaledb-1.7.0', 'ts_tablespace_attach' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION detach_tablespace(
    tablespace NAME,
    hypertable REGCLASS = NULL,
    if_attached BOOLEAN = false
) RETURNS INTEGER
AS '$libdir/timescaledb-1.7.0', 'ts_tablespace_detach' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION detach_tablespaces(hypertable REGCLASS) RETURNS INTEGER
AS '$libdir/timescaledb-1.7.0', 'ts_tablespace_detach_all_from_hypertable' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION show_tablespaces(hypertable REGCLASS) RETURNS SETOF NAME
AS '$libdir/timescaledb-1.7.0', 'ts_tablespace_show' LANGUAGE C VOLATILE STRICT;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

DROP EVENT TRIGGER IF EXISTS timescaledb_ddl_command_end;

CREATE OR REPLACE FUNCTION _timescaledb_internal.process_ddl_event() RETURNS event_trigger
AS '$libdir/timescaledb-1.7.0', 'ts_timescaledb_process_ddl_event' LANGUAGE C;

--EVENT TRIGGER MUST exclude the ALTER EXTENSION tag.
CREATE EVENT TRIGGER timescaledb_ddl_command_end ON ddl_command_end
WHEN TAG IN ('ALTER TABLE','CREATE TRIGGER','CREATE TABLE','CREATE INDEX','ALTER INDEX', 'DROP TABLE', 'DROP INDEX')
EXECUTE PROCEDURE _timescaledb_internal.process_ddl_event();

DROP EVENT TRIGGER IF EXISTS timescaledb_ddl_sql_drop;
CREATE EVENT TRIGGER timescaledb_ddl_sql_drop ON sql_drop
EXECUTE PROCEDURE _timescaledb_internal.process_ddl_event();
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION _timescaledb_internal.first_sfunc(internal, anyelement, "any")
RETURNS internal
AS '$libdir/timescaledb-1.7.0', 'ts_first_sfunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.first_combinefunc(internal, internal)
RETURNS internal
AS '$libdir/timescaledb-1.7.0', 'ts_first_combinefunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.last_sfunc(internal, anyelement, "any")
RETURNS internal
AS '$libdir/timescaledb-1.7.0', 'ts_last_sfunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.last_combinefunc(internal, internal)
RETURNS internal
AS '$libdir/timescaledb-1.7.0', 'ts_last_combinefunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.bookend_finalfunc(internal, anyelement, "any")
RETURNS anyelement
AS '$libdir/timescaledb-1.7.0', 'ts_bookend_finalfunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.bookend_serializefunc(internal)
RETURNS bytea
AS '$libdir/timescaledb-1.7.0', 'ts_bookend_serializefunc'
LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.bookend_deserializefunc(bytea, internal)
RETURNS internal
AS '$libdir/timescaledb-1.7.0', 'ts_bookend_deserializefunc'
LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- time_bucket returns the left edge of the bucket where ts falls into.
-- Buckets span an interval of time equal to the bucket_width and are aligned with the epoch.
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts TIMESTAMP) RETURNS TIMESTAMP
	AS '$libdir/timescaledb-1.7.0', 'ts_timestamp_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;

-- bucketing of timestamptz happens at UTC time
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts TIMESTAMPTZ) RETURNS TIMESTAMPTZ
	AS '$libdir/timescaledb-1.7.0', 'ts_timestamptz_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;

--bucketing on date should not do any timezone conversion
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts DATE) RETURNS DATE
	AS '$libdir/timescaledb-1.7.0', 'ts_date_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;

--bucketing with origin
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts TIMESTAMP, origin TIMESTAMP) RETURNS TIMESTAMP
	AS '$libdir/timescaledb-1.7.0', 'ts_timestamp_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts TIMESTAMPTZ, origin TIMESTAMPTZ) RETURNS TIMESTAMPTZ
	AS '$libdir/timescaledb-1.7.0', 'ts_timestamptz_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts DATE, origin DATE) RETURNS DATE
	AS '$libdir/timescaledb-1.7.0', 'ts_date_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;

-- bucketing of int
CREATE OR REPLACE FUNCTION time_bucket(bucket_width SMALLINT, ts SMALLINT) RETURNS SMALLINT
	AS '$libdir/timescaledb-1.7.0', 'ts_int16_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INT, ts INT) RETURNS INT
	AS '$libdir/timescaledb-1.7.0', 'ts_int32_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;
CREATE OR REPLACE FUNCTION time_bucket(bucket_width BIGINT, ts BIGINT) RETURNS BIGINT
	AS '$libdir/timescaledb-1.7.0', 'ts_int64_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;

-- bucketing of int with offset
CREATE OR REPLACE FUNCTION time_bucket(bucket_width SMALLINT, ts SMALLINT, "offset" SMALLINT) RETURNS SMALLINT
	AS '$libdir/timescaledb-1.7.0', 'ts_int16_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INT, ts INT, "offset" INT) RETURNS INT
	AS '$libdir/timescaledb-1.7.0', 'ts_int32_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;
CREATE OR REPLACE FUNCTION time_bucket(bucket_width BIGINT, ts BIGINT, "offset" BIGINT) RETURNS BIGINT
	AS '$libdir/timescaledb-1.7.0', 'ts_int64_bucket' LANGUAGE C IMMUTABLE PARALLEL SAFE STRICT;

-- If an interval is given as the third argument, the bucket alignment is offset by the interval.
CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts TIMESTAMP, "offset" INTERVAL)
    RETURNS TIMESTAMP LANGUAGE SQL IMMUTABLE PARALLEL SAFE STRICT AS
$BODY$
    SELECT @extschema@.time_bucket(bucket_width, ts-"offset")+"offset";
$BODY$;

CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts TIMESTAMPTZ, "offset" INTERVAL)
    RETURNS TIMESTAMPTZ LANGUAGE SQL IMMUTABLE PARALLEL SAFE STRICT AS
$BODY$
    SELECT @extschema@.time_bucket(bucket_width, ts-"offset")+"offset";
$BODY$;

CREATE OR REPLACE FUNCTION time_bucket(bucket_width INTERVAL, ts DATE, "offset" INTERVAL)
    RETURNS DATE LANGUAGE SQL IMMUTABLE PARALLEL SAFE STRICT AS
$BODY$
    SELECT (@extschema@.time_bucket(bucket_width, ts-"offset")+"offset")::date;
$BODY$;

-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION _timescaledb_internal.get_git_commit() RETURNS TEXT
    AS '$libdir/timescaledb-1.7.0', 'ts_get_git_commit' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.get_os_info()
    RETURNS TABLE(sysname TEXT, version TEXT, release TEXT, version_pretty TEXT)
    AS '$libdir/timescaledb-1.7.0', 'ts_get_os_info' LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION get_telemetry_report(always_display_report boolean DEFAULT false) RETURNS TEXT
    AS '$libdir/timescaledb-1.7.0', 'ts_get_telemetry_report' LANGUAGE C STABLE PARALLEL SAFE;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- This file contains utility functions to get the relation size
-- of hypertables, chunks, and indexes on hypertables.

-- Get relation size of hypertable
-- like pg_relation_size(hypertable)
-- (https://www.postgresql.org/docs/9.6/static/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE)
--
-- main_table - hypertable to get size of
--
-- Returns:
-- table_bytes        - Disk space used by main_table (like pg_relation_size(main_table))
-- index_bytes        - Disk space used by indexes
-- toast_bytes        - Disk space of toast tables
-- total_bytes        - Total disk space used by the specified table, including all indexes and TOAST data

CREATE OR REPLACE FUNCTION hypertable_relation_size(
    main_table              REGCLASS
)
RETURNS TABLE (table_bytes BIGINT,
               index_bytes BIGINT,
               toast_bytes BIGINT,
               total_bytes BIGINT
               ) LANGUAGE PLPGSQL STABLE STRICT
               AS
$BODY$
DECLARE
        table_name       NAME;
        schema_name      NAME;
BEGIN
        SELECT relname, nspname
        INTO STRICT table_name, schema_name
        FROM pg_class c
        INNER JOIN pg_namespace n ON (n.OID = c.relnamespace)
        WHERE c.OID = main_table;

        RETURN QUERY EXECUTE format(
        $$
        SELECT table_bytes,
               index_bytes,
               toast_bytes,
               total_bytes
               FROM (
               SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
                      SELECT
                      sum(pg_total_relation_size(format('%%I.%%I', c.schema_name, c.table_name)))::bigint as total_bytes,
                      sum(pg_indexes_size(format('%%I.%%I', c.schema_name, c.table_name)))::bigint AS index_bytes,
                      sum(pg_total_relation_size(reltoastrelid))::bigint AS toast_bytes
                      FROM
                      _timescaledb_catalog.hypertable h,
                      _timescaledb_catalog.chunk c,
                      pg_class pgc,
                      pg_namespace pns
                      WHERE h.schema_name = %L
                      AND c.dropped = false
                      AND h.table_name = %L
                      AND c.hypertable_id = h.id
                      AND pgc.relname = h.table_name
                      AND pns.oid = pgc.relnamespace
                      AND pns.nspname = h.schema_name
                      AND relkind = 'r'
                      ) sub1
               ) sub2;
        $$,
        schema_name, table_name);

END;
$BODY$;

CREATE OR REPLACE FUNCTION _timescaledb_internal.range_value_to_pretty(
    time_value      BIGINT,
    column_type     REGTYPE
)
    RETURNS TEXT LANGUAGE PLPGSQL STABLE AS
$BODY$
DECLARE
BEGIN
    IF NOT _timescaledb_internal.dimension_is_finite(time_value) THEN
        RETURN '';
    END IF;
    IF time_value IS NULL THEN
        RETURN format('%L', NULL);
    END IF;
    CASE column_type
      WHEN 'BIGINT'::regtype, 'INTEGER'::regtype, 'SMALLINT'::regtype THEN
        RETURN format('%L', time_value); -- scale determined by user.
      WHEN 'TIMESTAMP'::regtype, 'TIMESTAMPTZ'::regtype THEN
        -- assume time_value is in microsec
        RETURN format('%1$L', _timescaledb_internal.to_timestamp(time_value)); -- microseconds
      WHEN 'DATE'::regtype THEN
        RETURN format('%L', timezone('UTC',_timescaledb_internal.to_timestamp(time_value))::date);
      ELSE
        RETURN time_value;
    END CASE;
END
$BODY$;


CREATE OR REPLACE FUNCTION _timescaledb_internal.partitioning_column_to_pretty(
    d   _timescaledb_catalog.dimension
)
    RETURNS TEXT LANGUAGE PLPGSQL STABLE STRICT AS
$BODY$
DECLARE
BEGIN
        IF d.partitioning_func IS NULL THEN
           RETURN d.column_name;
        ELSE
           RETURN format('%I.%I(%I)', d.partitioning_func_schema, d.partitioning_func, d.column_name);
        END IF;
END
$BODY$;


-- Get relation size of hypertable
-- like pg_relation_size(hypertable)
-- (https://www.postgresql.org/docs/9.6/static/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE)
--
-- main_table - hypertable to get size of
--
-- Returns:
-- table_size         - Pretty output of table_bytes
-- index_bytes        - Pretty output of index_bytes
-- toast_bytes        - Pretty output of toast_bytes
-- total_size         - Pretty output of total_bytes

CREATE OR REPLACE FUNCTION hypertable_relation_size_pretty(
    main_table              REGCLASS
)
RETURNS TABLE (table_size  TEXT,
               index_size  TEXT,
               toast_size  TEXT,
               total_size  TEXT) LANGUAGE PLPGSQL STABLE STRICT
               AS
$BODY$
DECLARE
        table_name       NAME;
        schema_name      NAME;
BEGIN
        RETURN QUERY
        SELECT pg_size_pretty(table_bytes) as table,
               pg_size_pretty(index_bytes) as index,
               pg_size_pretty(toast_bytes) as toast,
               pg_size_pretty(total_bytes) as total
               FROM @extschema@.hypertable_relation_size(main_table);

END;
$BODY$;


-- Get relation size of the chunks of an hypertable
-- like pg_relation_size
-- (https://www.postgresql.org/docs/9.6/static/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE)
--
-- main_table - hypertable to get size of
--
-- Returns:
-- chunk_id                      - Timescaledb id of a chunk
-- chunk_table                   - Table used for the chunk
-- partitioning_columns          - Partitioning column names
-- partitioning_column_types     - Type of partitioning columns
-- partitioning_hash_functions   - Hash functions of partitioning columns
-- ranges                        - Partition ranges for each dimension of the chunk
-- table_bytes                   - Disk space used by main_table
-- index_bytes                   - Disk space used by indexes
-- toast_bytes                   - Disk space of toast tables
-- total_bytes                   - Disk space used in total

CREATE OR REPLACE FUNCTION chunk_relation_size(
    main_table              REGCLASS
)
RETURNS TABLE (chunk_id INT,
               chunk_table TEXT,
               partitioning_columns NAME[],
               partitioning_column_types REGTYPE[],
               partitioning_hash_functions TEXT[],
               ranges int8range[],
               table_bytes BIGINT,
               index_bytes BIGINT,
               toast_bytes BIGINT,
               total_bytes BIGINT)
               LANGUAGE PLPGSQL STABLE STRICT
               AS
$BODY$
DECLARE
        table_name       NAME;
        schema_name      NAME;
BEGIN
        SELECT relname, nspname
        INTO STRICT table_name, schema_name
        FROM pg_class c
        INNER JOIN pg_namespace n ON (n.OID = c.relnamespace)
        WHERE c.OID = main_table;

        RETURN QUERY EXECUTE format(
        $$

        SELECT chunk_id,
        chunk_table,
        partitioning_columns,
        partitioning_column_types,
        partitioning_hash_functions,
        ranges,
        table_bytes,
        index_bytes,
        toast_bytes,
        total_bytes
        FROM (
        SELECT *,
              total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes
              FROM (
               SELECT c.id as chunk_id,
               format('%%I.%%I', c.schema_name, c.table_name) as chunk_table,
               pg_total_relation_size(format('%%I.%%I', c.schema_name, c.table_name)) AS total_bytes,
               pg_indexes_size(format('%%I.%%I', c.schema_name, c.table_name)) AS index_bytes,
               pg_total_relation_size(reltoastrelid) AS toast_bytes,
               array_agg(d.column_name ORDER BY d.interval_length, d.column_name ASC) as partitioning_columns,
               array_agg(d.column_type ORDER BY d.interval_length, d.column_name ASC) as partitioning_column_types,
               array_agg(d.partitioning_func_schema || '.' || d.partitioning_func ORDER BY d.interval_length, d.column_name ASC) as partitioning_hash_functions,
               array_agg(int8range(range_start, range_end) ORDER BY d.interval_length, d.column_name ASC) as ranges
               FROM
               _timescaledb_catalog.hypertable h,
               _timescaledb_catalog.chunk c,
               _timescaledb_catalog.chunk_constraint cc,
               _timescaledb_catalog.dimension d,
               _timescaledb_catalog.dimension_slice ds,
               pg_class pgc,
               pg_namespace pns
               WHERE h.schema_name = %L
                     AND h.table_name = %L
                     AND pgc.relname = c.table_name
                     AND pns.oid = pgc.relnamespace
                     AND pns.nspname = c.schema_name
                     AND relkind = 'r'
                     AND c.hypertable_id = h.id
                     AND c.id = cc.chunk_id
                     AND cc.dimension_slice_id = ds.id
                     AND ds.dimension_id = d.id
               GROUP BY c.id, pgc.reltoastrelid, pgc.oid ORDER BY c.id
               ) sub1
        ) sub2;
        $$,
        schema_name, table_name);

END;
$BODY$;

-- Get relation size of the chunks of an hypertable
-- like pg_relation_size
-- (https://www.postgresql.org/docs/9.6/static/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE)
--
-- main_table - hypertable to get size of
--
-- Returns:
-- chunk_id                      - Timescaledb id of a chunk
-- chunk_table                   - Table used for the chunk
-- partitioning_columns          - Partitioning column names
-- partitioning_column_types     - Type of partitioning columns
-- partitioning_hash_functions   - Hash functions of partitioning columns
-- ranges                        - Partition ranges for each dimension of the chunk
-- table_size                    - Pretty output of table_bytes
-- index_size                    - Pretty output of index_bytes
-- toast_size                    - Pretty output of toast_bytes
-- total_size                    - Pretty output of total_bytes


CREATE OR REPLACE FUNCTION chunk_relation_size_pretty(
    main_table              REGCLASS
)
RETURNS TABLE (chunk_id INT,
               chunk_table TEXT,
               partitioning_columns NAME[],
               partitioning_column_types REGTYPE[],
               partitioning_hash_functions TEXT[],
               ranges TEXT[],
               table_size  TEXT,
               index_size  TEXT,
               toast_size  TEXT,
               total_size  TEXT
               )
               LANGUAGE PLPGSQL STABLE STRICT
               AS
$BODY$
DECLARE
        table_name       NAME;
        schema_name      NAME;
BEGIN
        SELECT relname, nspname
        INTO STRICT table_name, schema_name
        FROM pg_class c
        INNER JOIN pg_namespace n ON (n.OID = c.relnamespace)
        WHERE c.OID = main_table;

        RETURN QUERY EXECUTE format(
        $$

        SELECT chunk_id,
        chunk_table,
        partitioning_columns,
        partitioning_column_types,
        partitioning_functions,
        ranges,
        pg_size_pretty(table_bytes) AS table,
        pg_size_pretty(index_bytes) AS index,
        pg_size_pretty(toast_bytes) AS toast,
        pg_size_pretty(total_bytes) AS total
        FROM (
        SELECT *,
              total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes
              FROM (
               SELECT c.id as chunk_id,
               format('%%I.%%I', c.schema_name, c.table_name) as chunk_table,
               pg_total_relation_size(format('%%I.%%I', c.schema_name, c.table_name)) AS total_bytes,
               pg_indexes_size(format('%%I.%%I', c.schema_name, c.table_name)) AS index_bytes,
               pg_total_relation_size(reltoastrelid) AS toast_bytes,
               array_agg(d.column_name ORDER BY d.interval_length, d.column_name ASC) as partitioning_columns,
               array_agg(d.column_type ORDER BY d.interval_length, d.column_name ASC) as partitioning_column_types,
               array_agg(d.partitioning_func_schema || '.' || d.partitioning_func ORDER BY d.interval_length, d.column_name ASC) as partitioning_functions,
               array_agg('[' || _timescaledb_internal.range_value_to_pretty(range_start, column_type) ||
                         ',' ||
                         _timescaledb_internal.range_value_to_pretty(range_end, column_type) || ')' ORDER BY d.interval_length, d.column_name ASC) as ranges
               FROM
               _timescaledb_catalog.hypertable h,
               _timescaledb_catalog.chunk c,
               _timescaledb_catalog.chunk_constraint cc,
               _timescaledb_catalog.dimension d,
               _timescaledb_catalog.dimension_slice ds,
               pg_class pgc,
               pg_namespace pns
               WHERE h.schema_name = %L
                     AND h.table_name = %L
                     AND pgc.relname = c.table_name
                     AND pns.oid = pgc.relnamespace
                     AND pns.nspname = c.schema_name
                     AND relkind = 'r'
                     AND c.hypertable_id = h.id
                     AND c.id = cc.chunk_id
                     AND cc.dimension_slice_id = ds.id
                     AND ds.dimension_id = d.id
               GROUP BY c.id, pgc.reltoastrelid, pgc.oid ORDER BY c.id
               ) sub1
        ) sub2;
        $$,
        schema_name, table_name);

END;
$BODY$;


-- Get sizes of indexes on a hypertable
--
-- main_table - hypertable to get index sizes of
--
-- Returns:
-- index_name           - index on hyper table
-- total_bytes          - size of index on disk

CREATE OR REPLACE FUNCTION indexes_relation_size(
    main_table              REGCLASS
)
RETURNS TABLE (index_name TEXT,
               total_bytes BIGINT)
               LANGUAGE PLPGSQL STABLE STRICT
               AS
$BODY$
<<main>>
DECLARE
        table_name       NAME;
        schema_name      NAME;
BEGIN
        SELECT relname, nspname
        INTO STRICT table_name, schema_name
        FROM pg_class c
        INNER JOIN pg_namespace n ON (n.OID = c.relnamespace)
        WHERE c.OID = main_table;

        RETURN QUERY
        SELECT format('%I.%I', h.schema_name, ci.hypertable_index_name),
               sum(pg_relation_size(c.oid))::bigint
        FROM
        pg_class c,
        pg_namespace n,
        _timescaledb_catalog.hypertable h,
        _timescaledb_catalog.chunk ch,
        _timescaledb_catalog.chunk_index ci
        WHERE ch.schema_name = n.nspname
            AND c.relnamespace = n.oid
            AND c.relname = ci.index_name
            AND ch.id = ci.chunk_id
            AND h.id = ci.hypertable_id
            AND h.schema_name = main.schema_name
            AND h.table_name = main.table_name
        GROUP BY h.schema_name, ci.hypertable_index_name;
END;
$BODY$;


-- Get sizes of indexes on a hypertable
--
-- main_table - hypertable to get index sizes of
--
-- Returns:
-- index_name           - index on hyper table
-- total_size           - pretty output of total_bytes

CREATE OR REPLACE FUNCTION indexes_relation_size_pretty(
    main_table              REGCLASS
)
RETURNS TABLE (index_name TEXT,
               total_size TEXT) LANGUAGE PLPGSQL STABLE STRICT
               AS
$BODY$
BEGIN
        RETURN QUERY
        SELECT s.index_name,
               pg_size_pretty(s.total_bytes)
        FROM @extschema@.indexes_relation_size(main_table) s;
END;
$BODY$;


-- Convenience function to return approximate row count
--
-- main_table - hypertable to get approximate row count for; if NULL, get count
--              for all hypertables
--
-- Returns:
-- schema_name      - Schema name of the hypertable
-- table_name       - Table name of the hypertable
-- row_estimate     - Estimated number of rows according to catalog tables
CREATE OR REPLACE FUNCTION hypertable_approximate_row_count(
    main_table REGCLASS = NULL
)
    RETURNS TABLE (schema_name NAME,
                   table_name NAME,
                   row_estimate BIGINT
                  ) LANGUAGE PLPGSQL VOLATILE
    AS
$BODY$
<<main>>
DECLARE
        table_name       NAME;
        schema_name      NAME;
BEGIN
        IF main_table IS NOT NULL THEN
            SELECT relname, nspname
            INTO STRICT table_name, schema_name
            FROM pg_class c
            INNER JOIN pg_namespace n ON (n.OID = c.relnamespace)
            WHERE c.OID = main_table;
        END IF;

-- Thanks to @fvannee on Github for providing the initial draft
-- of this query
        RETURN QUERY
        SELECT h.schema_name,
            h.table_name,
            row_estimate.row_estimate
        FROM _timescaledb_catalog.hypertable h
        CROSS JOIN LATERAL (
            SELECT sum(cl.reltuples)::BIGINT AS row_estimate
            FROM _timescaledb_catalog.chunk c
            JOIN pg_class cl ON cl.relname = c.table_name
            WHERE c.hypertable_id = h.id
            GROUP BY h.schema_name, h.table_name
        ) row_estimate
        WHERE (main.table_name IS NULL OR h.table_name = main.table_name)
        AND (main.schema_name IS NULL OR h.schema_name = main.schema_name)
        ORDER BY h.schema_name, h.table_name;
END
$BODY$;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_sfunc (state INTERNAL, val DOUBLE PRECISION, MIN DOUBLE PRECISION, MAX DOUBLE PRECISION, nbuckets INTEGER)
RETURNS INTERNAL
AS '$libdir/timescaledb-1.7.0', 'ts_hist_sfunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_combinefunc(state1 INTERNAL, state2 INTERNAL)
RETURNS INTERNAL
AS '$libdir/timescaledb-1.7.0', 'ts_hist_combinefunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_serializefunc(INTERNAL)
RETURNS bytea
AS '$libdir/timescaledb-1.7.0', 'ts_hist_serializefunc'
LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_deserializefunc(bytea, INTERNAL)
RETURNS INTERNAL
AS '$libdir/timescaledb-1.7.0', 'ts_hist_deserializefunc'
LANGUAGE C IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.hist_finalfunc(state INTERNAL, val DOUBLE PRECISION, MIN DOUBLE PRECISION, MAX DOUBLE PRECISION, nbuckets INTEGER)
RETURNS INTEGER[]
AS '$libdir/timescaledb-1.7.0', 'ts_hist_finalfunc'
LANGUAGE C IMMUTABLE PARALLEL SAFE;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- This file contains infrastructure for cache invalidation of TimescaleDB
-- metadata caches kept in C. Please look at cache_invalidate.c for a
-- description of how this works.
CREATE TABLE IF NOT EXISTS  _timescaledb_cache.cache_inval_hypertable();

-- For notifying the scheduler of changes to the bgw_job table.
CREATE TABLE IF NOT EXISTS  _timescaledb_cache.cache_inval_bgw_job();

-- This is pretty subtle. We create this dummy cache_inval_extension table
-- solely for the purpose of getting a relcache invalidation event when it is
-- deleted on DROP extension. It has no related triggers. When the table is
-- invalidated, all backends will be notified and will know that they must
-- invalidate all cached information, including catalog table and index OIDs,
-- etc.
CREATE TABLE IF NOT EXISTS  _timescaledb_cache.cache_inval_extension();

-- not actually strictly needed but good for sanity as all tables should be dumped.
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_cache.cache_inval_hypertable', '');
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_cache.cache_inval_extension', '');
SELECT pg_catalog.pg_extension_config_dump('_timescaledb_cache.cache_inval_bgw_job', '');

GRANT SELECT ON ALL TABLES IN SCHEMA _timescaledb_cache TO PUBLIC;

-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION _timescaledb_internal.restart_background_workers()
RETURNS BOOL
AS '$libdir/timescaledb', 'ts_bgw_db_workers_restart'
LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.stop_background_workers()
RETURNS BOOL
AS '$libdir/timescaledb', 'ts_bgw_db_workers_stop'
LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.start_background_workers()
RETURNS BOOL
AS '$libdir/timescaledb', 'ts_bgw_db_workers_start'
LANGUAGE C VOLATILE;

INSERT INTO _timescaledb_config.bgw_job (id, application_name, job_type, schedule_INTERVAL, max_runtime, max_retries, retry_period) VALUES
(1, 'Telemetry Reporter', 'telemetry_and_version_check_if_enabled', INTERVAL '24h', INTERVAL '100s', -1, INTERVAL '1h')
ON CONFLICT (id) DO NOTHING;

CREATE OR REPLACE FUNCTION add_drop_chunks_policy(hypertable REGCLASS, older_than "any", cascade BOOL = FALSE, if_not_exists BOOL = false, cascade_to_materializations BOOL = false)
RETURNS INTEGER
AS '$libdir/timescaledb-1.7.0', 'ts_add_drop_chunks_policy'
LANGUAGE C VOLATILE STRICT;

CREATE OR REPLACE FUNCTION add_reorder_policy(hypertable REGCLASS, index_name NAME, if_not_exists BOOL = false) RETURNS INTEGER
AS '$libdir/timescaledb-1.7.0', 'ts_add_reorder_policy'
LANGUAGE C VOLATILE STRICT;

CREATE OR REPLACE FUNCTION add_compress_chunks_policy(hypertable REGCLASS, older_than "any", if_not_exists BOOL = false)
RETURNS INTEGER
AS '$libdir/timescaledb-1.7.0', 'ts_add_compress_chunks_policy'
LANGUAGE C VOLATILE STRICT;

CREATE OR REPLACE FUNCTION remove_drop_chunks_policy(hypertable REGCLASS, if_exists BOOL = false) RETURNS VOID
AS '$libdir/timescaledb-1.7.0', 'ts_remove_drop_chunks_policy'
LANGUAGE C VOLATILE STRICT;

CREATE OR REPLACE FUNCTION remove_reorder_policy(hypertable REGCLASS, if_exists BOOL = false) RETURNS VOID
AS '$libdir/timescaledb-1.7.0', 'ts_remove_reorder_policy'
LANGUAGE C VOLATILE STRICT;

CREATE OR REPLACE FUNCTION remove_compress_chunks_policy(hypertable REGCLASS, if_exists BOOL = false) RETURNS BOOL 
AS '$libdir/timescaledb-1.7.0', 'ts_remove_compress_chunks_policy'
LANGUAGE C VOLATILE STRICT;

-- Returns the updated job schedule values
CREATE OR REPLACE FUNCTION alter_job_schedule(
    job_id INTEGER,
    schedule_interval INTERVAL = NULL,
    max_runtime INTERVAL = NULL,
    max_retries INTEGER = NULL,
    retry_period INTERVAL = NULL,
    if_exists BOOL = FALSE,
    next_start TIMESTAMPTZ = NULL
)
RETURNS TABLE (job_id INTEGER, schedule_interval INTERVAL, max_runtime INTERVAL, max_retries INTEGER, retry_period INTERVAL, next_start TIMESTAMPTZ)
AS '$libdir/timescaledb-1.7.0', 'ts_alter_job_schedule'
LANGUAGE C VOLATILE;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION _timescaledb_internal.generate_uuid() RETURNS UUID
AS '$libdir/timescaledb-1.7.0', 'ts_uuid_generate' LANGUAGE C VOLATILE STRICT;

-- Insert uuid and install_timestamp on database creation. Don't
-- create exported_uuid because it gets exported and installed during
-- pg_dump, which would cause a conflict.
INSERT INTO _timescaledb_catalog.metadata
SELECT 'uuid', _timescaledb_internal.generate_uuid(), TRUE ON CONFLICT DO NOTHING;
INSERT INTO _timescaledb_catalog.metadata
SELECT 'install_timestamp', now(), TRUE ON CONFLICT DO NOTHING;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE SCHEMA IF NOT EXISTS timescaledb_information;

-- Convenience view to list all hypertables and their space usage
CREATE OR REPLACE VIEW timescaledb_information.hypertable AS
WITH ht_size as (
  SELECT ht.id, ht.schema_name AS table_schema,
    ht.table_name,
    t.tableowner AS table_owner,
    ht.num_dimensions,
    (SELECT count(1)
     FROM _timescaledb_catalog.chunk ch
     WHERE ch.hypertable_id=ht.id
    ) AS num_chunks,
    bsize.table_bytes,
    bsize.index_bytes,
    bsize.toast_bytes,
    bsize.total_bytes
  FROM _timescaledb_catalog.hypertable ht
    LEFT OUTER JOIN pg_tables t ON ht.table_name=t.tablename AND ht.schema_name=t.schemaname
    LEFT OUTER JOIN LATERAL @extschema@.hypertable_relation_size(
      CASE WHEN has_schema_privilege(ht.schema_name,'USAGE') THEN format('%I.%I',ht.schema_name,ht.table_name) ELSE NULL END
    ) bsize ON true
),
compht_size as
(
  select srcht.id,
  sum(map.compressed_heap_size) as heap_bytes,
  sum(map.compressed_index_size) as index_bytes,
  sum(map.compressed_toast_size) as toast_bytes,
  sum(map.compressed_heap_size) + sum(map.compressed_toast_size) + sum(map.compressed_index_size) as total_bytes
 FROM _timescaledb_catalog.chunk srcch, _timescaledb_catalog.compression_chunk_size map,
      _timescaledb_catalog.hypertable srcht
 where map.chunk_id = srcch.id and srcht.id = srcch.hypertable_id
 group by srcht.id
)
select hts.table_schema, hts.table_name, hts.table_owner, 
       hts.num_dimensions, hts.num_chunks,
       pg_size_pretty( COALESCE(hts.table_bytes + compht_size.heap_bytes, hts.table_bytes)) as table_size,
       pg_size_pretty( COALESCE(hts.index_bytes + compht_size.index_bytes , hts.index_bytes, compht_size.index_bytes)) as index_size,
       pg_size_pretty( COALESCE(hts.toast_bytes + compht_size.toast_bytes, hts.toast_bytes, compht_size.toast_bytes)) as toast_size,
       pg_size_pretty( COALESCE(hts.total_bytes + compht_size.total_bytes, hts.total_bytes)) as total_size
FROM ht_size hts LEFT OUTER JOIN compht_size 
ON hts.id = compht_size.id;

CREATE OR REPLACE VIEW timescaledb_information.license AS
  SELECT _timescaledb_internal.license_edition() as edition,
         _timescaledb_internal.license_expiration_time() <= now() AS expired,
         _timescaledb_internal.license_expiration_time() AS expiration_time;

CREATE OR REPLACE VIEW timescaledb_information.drop_chunks_policies as
  SELECT format('%1$I.%2$I', ht.schema_name, ht.table_name)::regclass as hypertable, p.older_than, p.cascade, p.job_id, j.schedule_interval,
    j.max_runtime, j.max_retries, j.retry_period, p.cascade_to_materializations
  FROM _timescaledb_config.bgw_policy_drop_chunks p
    INNER JOIN _timescaledb_catalog.hypertable ht ON p.hypertable_id = ht.id
    INNER JOIN _timescaledb_config.bgw_job j ON p.job_id = j.id;

CREATE OR REPLACE VIEW timescaledb_information.reorder_policies as
  SELECT format('%1$I.%2$I', ht.schema_name, ht.table_name)::regclass as hypertable, p.hypertable_index_name, p.job_id, j.schedule_interval,
    j.max_runtime, j.max_retries, j.retry_period
  FROM _timescaledb_config.bgw_policy_reorder p
    INNER JOIN _timescaledb_catalog.hypertable ht ON p.hypertable_id = ht.id
    INNER JOIN _timescaledb_config.bgw_job j ON p.job_id = j.id;

CREATE OR REPLACE VIEW timescaledb_information.policy_stats as
  SELECT format('%1$I.%2$I', ht.schema_name, ht.table_name)::regclass as hypertable, p.job_id, j.job_type, js.last_run_success, js.last_finish, js.last_successful_finish, js.last_start, js.next_start,
    js.total_runs, js.total_failures
  FROM (SELECT job_id, hypertable_id FROM _timescaledb_config.bgw_policy_reorder
        UNION SELECT job_id, hypertable_id FROM _timescaledb_config.bgw_policy_drop_chunks
        UNION SELECT job_id, hypertable_id FROM _timescaledb_config.bgw_policy_compress_chunks
        UNION SELECT job_id, raw_hypertable_id FROM _timescaledb_catalog.continuous_agg) p
    INNER JOIN _timescaledb_catalog.hypertable ht ON p.hypertable_id = ht.id
    INNER JOIN _timescaledb_config.bgw_job j ON p.job_id = j.id
    INNER JOIN _timescaledb_internal.bgw_job_stat js on p.job_id = js.job_id
  ORDER BY ht.schema_name, ht.table_name;

-- views for continuous aggregate queries ---
CREATE OR REPLACE VIEW timescaledb_information.continuous_aggregates as
  SELECT format('%1$I.%2$I', cagg.user_view_schema, cagg.user_view_name)::regclass as view_name,
    viewinfo.viewowner as view_owner,
    CASE _timescaledb_internal.get_time_type(cagg.raw_hypertable_id)
      WHEN 'TIMESTAMP'::regtype
        THEN _timescaledb_internal.to_interval(cagg.refresh_lag)::TEXT
      WHEN 'TIMESTAMPTZ'::regtype
        THEN _timescaledb_internal.to_interval(cagg.refresh_lag)::TEXT
      WHEN 'DATE'::regtype
        THEN _timescaledb_internal.to_interval(cagg.refresh_lag)::TEXT
      ELSE cagg.refresh_lag::TEXT
    END AS refresh_lag,
    bgwjob.schedule_interval as refresh_interval,
    CASE _timescaledb_internal.get_time_type(cagg.raw_hypertable_id)
      WHEN 'TIMESTAMP'::regtype
        THEN _timescaledb_internal.to_interval(cagg.max_interval_per_job)::TEXT
      WHEN 'TIMESTAMPTZ'::regtype
        THEN _timescaledb_internal.to_interval(cagg.max_interval_per_job)::TEXT
      WHEN 'DATE'::regtype
        THEN _timescaledb_internal.to_interval(cagg.max_interval_per_job)::TEXT
      ELSE cagg.max_interval_per_job::TEXT
    END AS max_interval_per_job,
    CASE
      WHEN cagg.ignore_invalidation_older_than = BIGINT '9223372036854775807'
        THEN NULL
      ELSE
	CASE _timescaledb_internal.get_time_type(cagg.raw_hypertable_id)
          WHEN 'TIMESTAMP'::regtype
            THEN _timescaledb_internal.to_interval(cagg.ignore_invalidation_older_than)::TEXT
          WHEN 'TIMESTAMPTZ'::regtype
            THEN _timescaledb_internal.to_interval(cagg.ignore_invalidation_older_than)::TEXT
          WHEN 'DATE'::regtype
            THEN _timescaledb_internal.to_interval(cagg.ignore_invalidation_older_than)::TEXT
          ELSE cagg.ignore_invalidation_older_than::TEXT
        END
    END AS ignore_invalidation_older_than,
    cagg.materialized_only,
    format('%1$I.%2$I', ht.schema_name, ht.table_name)::regclass as materialization_hypertable,
    directview.viewdefinition as view_definition
  FROM  _timescaledb_catalog.continuous_agg cagg,
        _timescaledb_catalog.hypertable ht, LATERAL
        ( select C.oid, pg_get_userbyid( C.relowner) as viewowner
          FROM pg_class C LEFT JOIN pg_namespace N on (N.oid = C.relnamespace)
          where C.relkind = 'v' and C.relname = cagg.user_view_name
          and N.nspname = cagg.user_view_schema ) viewinfo, LATERAL
        ( select schedule_interval
          FROM  _timescaledb_config.bgw_job
          where id = cagg.job_id ) bgwjob, LATERAL
        ( select pg_get_viewdef(C.oid) as viewdefinition
          FROM pg_class C LEFT JOIN pg_namespace N on (N.oid = C.relnamespace)
          where C.relkind = 'v' and C.relname = cagg.direct_view_name
          and N.nspname = cagg.direct_view_schema ) directview
  WHERE cagg.mat_hypertable_id = ht.id;

CREATE OR REPLACE VIEW timescaledb_information.continuous_aggregate_stats as
  SELECT format('%1$I.%2$I', cagg.user_view_schema, cagg.user_view_name)::regclass as view_name,
    CASE _timescaledb_internal.get_time_type(cagg.raw_hypertable_id)
      WHEN 'TIMESTAMP'::regtype
        THEN _timescaledb_internal.to_timestamp_without_timezone(ct.watermark)::TEXT
      WHEN 'TIMESTAMPTZ'::regtype
        THEN _timescaledb_internal.to_timestamp(ct.watermark)::TEXT
      WHEN 'DATE'::regtype
        THEN _timescaledb_internal.to_date(ct.watermark)::TEXT
      ELSE ct.watermark::TEXT
    END AS completed_threshold,
    CASE _timescaledb_internal.get_time_type(cagg.raw_hypertable_id)
      WHEN 'TIMESTAMP'::regtype
        THEN _timescaledb_internal.to_timestamp_without_timezone(it.watermark)::TEXT
      WHEN 'TIMESTAMPTZ'::regtype
        THEN _timescaledb_internal.to_timestamp(it.watermark)::TEXT
      WHEN 'DATE'::regtype
        THEN _timescaledb_internal.to_date(it.watermark)::TEXT
      ELSE it.watermark::TEXT
    END AS invalidation_threshold,
    cagg.job_id as job_id,
    bgw_job_stat.last_start as last_run_started_at,
    bgw_job_stat.last_successful_finish as last_successful_finish,
    CASE WHEN bgw_job_stat.last_finish < '4714-11-24 00:00:00+00 BC' THEN NULL 
         WHEN bgw_job_stat.last_finish IS NOT NULL THEN
              CASE WHEN bgw_job_stat.last_run_success = 't' THEN 'Success'
                   WHEN bgw_job_stat.last_run_success = 'f' THEN 'Failed'
              END
    END as last_run_status,
    CASE WHEN bgw_job_stat.last_finish < '4714-11-24 00:00:00+00 BC' THEN 'Running'
       WHEN bgw_job_stat.next_start IS NOT NULL THEN 'Scheduled'
    END as job_status,
    CASE WHEN bgw_job_stat.last_finish > bgw_job_stat.last_start THEN (bgw_job_stat.last_finish - bgw_job_stat.last_start)
    END as last_run_duration,
    bgw_job_stat.next_start as next_scheduled_run,
    bgw_job_stat.total_runs,
    bgw_job_stat.total_successes,
    bgw_job_stat.total_failures,
    bgw_job_stat.total_crashes
  FROM
    _timescaledb_catalog.continuous_agg as cagg
    LEFT JOIN _timescaledb_internal.bgw_job_stat as bgw_job_stat
    ON  ( cagg.job_id = bgw_job_stat.job_id )
    LEFT JOIN _timescaledb_catalog.continuous_aggs_invalidation_threshold as it
    ON ( cagg.raw_hypertable_id = it.hypertable_id)
    LEFT JOIN _timescaledb_catalog.continuous_aggs_completed_threshold as ct
    ON ( cagg.mat_hypertable_id = ct.materialization_id);

CREATE OR REPLACE VIEW  timescaledb_information.compressed_chunk_stats
AS
WITH mapq as
(select
  chunk_id,
  pg_size_pretty(map.uncompressed_heap_size) as uncompressed_heap_bytes,
  pg_size_pretty(map.uncompressed_index_size) as uncompressed_index_bytes,
  pg_size_pretty(map.uncompressed_toast_size) as uncompressed_toast_bytes,
  pg_size_pretty(map.uncompressed_heap_size + map.uncompressed_toast_size + map.uncompressed_index_size) as uncompressed_total_bytes,
  pg_size_pretty(map.compressed_heap_size) as compressed_heap_bytes,
  pg_size_pretty(map.compressed_index_size) as compressed_index_bytes,
  pg_size_pretty(map.compressed_toast_size) as compressed_toast_bytes,
  pg_size_pretty(map.compressed_heap_size + map.compressed_toast_size + map.compressed_index_size) as compressed_total_bytes
 FROM _timescaledb_catalog.compression_chunk_size map )
  SELECT format('%1$I.%2$I', srcht.schema_name, srcht.table_name)::regclass as hypertable_name,
  format('%1$I.%2$I', srcch.schema_name, srcch.table_name)::regclass as chunk_name,
  CASE WHEN srcch.compressed_chunk_id IS NULL THEN 'Uncompressed'::TEXT ELSE 'Compressed'::TEXT END as compression_status,
  mapq.uncompressed_heap_bytes,
  mapq.uncompressed_index_bytes,
  mapq.uncompressed_toast_bytes,
  mapq.uncompressed_total_bytes,
  mapq.compressed_heap_bytes,
  mapq.compressed_index_bytes,
  mapq.compressed_toast_bytes,
  mapq.compressed_total_bytes
  FROM _timescaledb_catalog.hypertable as srcht JOIN _timescaledb_catalog.chunk as srcch
  ON srcht.id = srcch.hypertable_id and srcht.compressed_hypertable_id IS NOT NULL and srcch.dropped = false
  LEFT JOIN mapq
  ON srcch.id = mapq.chunk_id ;

CREATE OR REPLACE VIEW  timescaledb_information.compressed_hypertable_stats
AS
  SELECT format('%1$I.%2$I', srcht.schema_name, srcht.table_name)::regclass as hypertable_name,
  ( select count(*) from _timescaledb_catalog.chunk where hypertable_id = srcht.id) as total_chunks, 
  count(*) as number_compressed_chunks,
  pg_size_pretty(sum(map.uncompressed_heap_size)) as uncompressed_heap_bytes,
  pg_size_pretty(sum(map.uncompressed_index_size)) as uncompressed_index_bytes,
  pg_size_pretty(sum(map.uncompressed_toast_size)) as uncompressed_toast_bytes,
  pg_size_pretty(sum(map.uncompressed_heap_size) + sum(map.uncompressed_toast_size) + sum(map.uncompressed_index_size)) as uncompressed_total_bytes,
  pg_size_pretty(sum(map.compressed_heap_size)) as compressed_heap_bytes,
  pg_size_pretty(sum(map.compressed_index_size)) as compressed_index_bytes,
  pg_size_pretty(sum(map.compressed_toast_size)) as compressed_toast_bytes,
  pg_size_pretty(sum(map.compressed_heap_size) + sum(map.compressed_toast_size) + sum(map.compressed_index_size)) as compressed_total_bytes
 FROM _timescaledb_catalog.chunk srcch, _timescaledb_catalog.compression_chunk_size map,
      _timescaledb_catalog.hypertable srcht
 where map.chunk_id = srcch.id and srcht.id = srcch.hypertable_id
 group by srcht.id;

GRANT USAGE ON SCHEMA timescaledb_information TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA timescaledb_information TO PUBLIC;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION time_bucket_gapfill(bucket_width SMALLINT, ts SMALLINT, start SMALLINT=NULL, finish SMALLINT=NULL) RETURNS SMALLINT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_int16_bucket' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION time_bucket_gapfill(bucket_width INT, ts INT, start INT=NULL, finish INT=NULL) RETURNS INT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_int32_bucket' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION time_bucket_gapfill(bucket_width BIGINT, ts BIGINT, start BIGINT=NULL, finish BIGINT=NULL) RETURNS BIGINT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_int64_bucket' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION time_bucket_gapfill(bucket_width INTERVAL, ts DATE, start DATE=NULL, finish DATE=NULL) RETURNS DATE
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_date_bucket' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION time_bucket_gapfill(bucket_width INTERVAL, ts TIMESTAMP, start TIMESTAMP=NULL, finish TIMESTAMP=NULL) RETURNS TIMESTAMP
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_timestamp_bucket' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION time_bucket_gapfill(bucket_width INTERVAL, ts TIMESTAMPTZ, start TIMESTAMPTZ=NULL, finish TIMESTAMPTZ=NULL) RETURNS TIMESTAMPTZ
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_timestamptz_bucket' LANGUAGE C VOLATILE PARALLEL SAFE;

-- locf function
CREATE OR REPLACE FUNCTION locf(value ANYELEMENT, prev ANYELEMENT=NULL, treat_null_as_missing BOOL=false) RETURNS ANYELEMENT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_marker' LANGUAGE C VOLATILE PARALLEL SAFE;

-- interpolate functions
CREATE OR REPLACE FUNCTION interpolate(value SMALLINT,prev RECORD=NULL,next RECORD=NULL) RETURNS SMALLINT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_marker' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION interpolate(value INT,prev RECORD=NULL,next RECORD=NULL) RETURNS INT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_marker' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION interpolate(value BIGINT,prev RECORD=NULL,next RECORD=NULL) RETURNS BIGINT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_marker' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION interpolate(value REAL,prev RECORD=NULL,next RECORD=NULL) RETURNS REAL
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_marker' LANGUAGE C VOLATILE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION interpolate(value FLOAT,prev RECORD=NULL,next RECORD=NULL) RETURNS FLOAT
	AS '$libdir/timescaledb-1.7.0', 'ts_gapfill_marker' LANGUAGE C VOLATILE PARALLEL SAFE;

-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

-- chunk - the OID of the chunk to be CLUSTERed
-- index - the OID of the index to be CLUSTERed on, or NULL to use the index
--         last used
CREATE OR REPLACE FUNCTION reorder_chunk(
    chunk REGCLASS,
    index REGCLASS=NULL,
    verbose BOOLEAN=FALSE
) RETURNS VOID AS '$libdir/timescaledb-1.7.0', 'ts_reorder_chunk' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION move_chunk(
    chunk REGCLASS,
    destination_tablespace Name,
    index_destination_tablespace Name=NULL,
    reorder_index REGCLASS=NULL,
    verbose BOOLEAN=FALSE
) RETURNS VOID AS '$libdir/timescaledb-1.7.0', 'ts_move_chunk' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION compress_chunk(
    uncompressed_chunk REGCLASS,
    if_not_compressed BOOLEAN = false
) RETURNS REGCLASS AS '$libdir/timescaledb-1.7.0', 'ts_compress_chunk' LANGUAGE C STRICT VOLATILE;

CREATE OR REPLACE FUNCTION decompress_chunk(
    uncompressed_chunk REGCLASS,
    if_compressed BOOLEAN = false
) RETURNS REGCLASS AS '$libdir/timescaledb-1.7.0', 'ts_decompress_chunk' LANGUAGE C STRICT VOLATILE;
-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION _timescaledb_internal.partialize_agg(arg ANYELEMENT)
RETURNS BYTEA AS '$libdir/timescaledb-1.7.0', 'ts_partialize_agg' LANGUAGE C VOLATILE;

CREATE OR REPLACE FUNCTION _timescaledb_internal.finalize_agg_sfunc(
tstate internal, aggfn TEXT, inner_agg_collation_schema NAME, inner_agg_collation_name NAME, inner_agg_input_types NAME[][], inner_agg_serialized_state BYTEA, return_type_dummy_val ANYELEMENT)
RETURNS internal
AS '$libdir/timescaledb-1.7.0', 'ts_finalize_agg_sfunc'
LANGUAGE C IMMUTABLE ;

CREATE OR REPLACE FUNCTION _timescaledb_internal.finalize_agg_ffunc(
tstate internal, aggfn TEXT, inner_agg_collation_schema NAME, inner_agg_collation_name NAME, inner_agg_input_types NAME[][], inner_agg_serialized_state BYTEA, return_type_dummy_val ANYELEMENT)
RETURNS anyelement
AS '$libdir/timescaledb-1.7.0', 'ts_finalize_agg_ffunc'
LANGUAGE C IMMUTABLE ;

-- This file and its contents are licensed under the Apache License 2.0.
-- Please see the included NOTICE for copyright information and
-- LICENSE-APACHE for a copy of the license.

CREATE OR REPLACE FUNCTION timescaledb_pre_restore() RETURNS BOOL AS
$BODY$
DECLARE
    db text;
BEGIN
    SELECT current_database() INTO db;
    EXECUTE format($$ALTER DATABASE %I SET timescaledb.restoring ='on'$$, db);
    SET SESSION timescaledb.restoring = 'on';
    PERFORM _timescaledb_internal.stop_background_workers();
    --exported uuid may be included in the dump so backup the version
    UPDATE _timescaledb_catalog.metadata SET key='exported_uuid_bak' WHERE key='exported_uuid';
    RETURN true;
END
$BODY$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION timescaledb_post_restore() RETURNS BOOL AS
$BODY$
DECLARE
    db text;
BEGIN
    SELECT current_database() INTO db;
    EXECUTE format($$ALTER DATABASE %I SET timescaledb.restoring ='off'$$, db);
    SET SESSION timescaledb.restoring='off';
    PERFORM _timescaledb_internal.restart_background_workers();

    --try to restore the backed up uuid, if the restore did not set one
    INSERT INTO _timescaledb_catalog.metadata
       SELECT 'exported_uuid', value, include_in_telemetry FROM _timescaledb_catalog.metadata WHERE key='exported_uuid_bak'
       ON CONFLICT DO NOTHING;
    DELETE FROM _timescaledb_catalog.metadata WHERE key='exported_uuid_bak';

    RETURN true;
END
$BODY$
LANGUAGE PLPGSQL;
