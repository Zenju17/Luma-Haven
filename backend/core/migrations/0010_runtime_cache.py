from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('core', '0009_mediafile')]
    operations = [migrations.RunSQL(
        sql='''CREATE TABLE core_runtime_cache (
            cache_key varchar(255) PRIMARY KEY,
            value text NOT NULL,
            expires timestamptz NOT NULL
        ); CREATE INDEX core_runtime_cache_expires ON core_runtime_cache (expires);''',
        reverse_sql='DROP TABLE core_runtime_cache;',
    )]
