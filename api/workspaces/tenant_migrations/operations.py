# api/workspaces/tenant_migrations/operations.py

class MigrationOperation:
    def database_forwards(self, schema_name, cursor):
        raise NotImplementedError("subclasses must implement database_forwards")

    def database_backwards(self, schema_name, cursor):
        raise NotImplementedError("subclasses must implement database_backwards")


class CreateTable(MigrationOperation):
    def __init__(self, table_name, columns, constraints=None):
        self.table_name = table_name
        self.columns = columns
        self.constraints = constraints or []

    def database_forwards(self, schema_name, cursor):
        cols_sql = []
        for name, definition in self.columns:
            cols_sql.append(f"{name} {definition}")
        
        for constraint in self.constraints:
            cols_sql.append(constraint)

        columns_str = ",\n    ".join(cols_sql)
        sql = f"CREATE TABLE IF NOT EXISTS {schema_name}.{self.table_name} (\n    {columns_str}\n);"
        cursor.execute(sql)

    def database_backwards(self, schema_name, cursor):
        sql = f"DROP TABLE IF EXISTS {schema_name}.{self.table_name} CASCADE;"
        cursor.execute(sql)


class DropTable(MigrationOperation):
    def __init__(self, table_name):
        self.table_name = table_name

    def database_forwards(self, schema_name, cursor):
        sql = f"DROP TABLE IF EXISTS {schema_name}.{self.table_name} CASCADE;"
        cursor.execute(sql)

    def database_backwards(self, schema_name, cursor):
        raise NotImplementedError("DropTable backward migration is not supported without column details.")


class AddColumn(MigrationOperation):
    def __init__(self, table_name, column_name, definition):
        self.table_name = table_name
        self.column_name = column_name
        self.definition = definition

    def database_forwards(self, schema_name, cursor):
        sql = f"ALTER TABLE {schema_name}.{self.table_name} ADD COLUMN {self.column_name} {self.definition};"
        cursor.execute(sql)

    def database_backwards(self, schema_name, cursor):
        sql = f"ALTER TABLE {schema_name}.{self.table_name} DROP COLUMN IF EXISTS {self.column_name};"
        cursor.execute(sql)


class RemoveColumn(MigrationOperation):
    def __init__(self, table_name, column_name, definition_for_rollback):
        self.table_name = table_name
        self.column_name = column_name
        self.definition_for_rollback = definition_for_rollback

    def database_forwards(self, schema_name, cursor):
        sql = f"ALTER TABLE {schema_name}.{self.table_name} DROP COLUMN IF EXISTS {self.column_name};"
        cursor.execute(sql)

    def database_backwards(self, schema_name, cursor):
        sql = f"ALTER TABLE {schema_name}.{self.table_name} ADD COLUMN {self.column_name} {self.definition_for_rollback};"
        cursor.execute(sql)


class RunSQL(MigrationOperation):
    def __init__(self, sql, reverse_sql=None):
        self.sql = sql
        self.reverse_sql = reverse_sql

    def database_forwards(self, schema_name, cursor):
        sql_formatted = self.sql.format(schema=schema_name)
        cursor.execute(sql_formatted)

    def database_backwards(self, schema_name, cursor):
        if self.reverse_sql:
            sql_formatted = self.reverse_sql.format(schema=schema_name)
            cursor.execute(sql_formatted)
        else:
            # If no reverse SQL is provided, treat it as irreversible or ignore
            pass
