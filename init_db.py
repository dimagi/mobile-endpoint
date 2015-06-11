from pg_utils import execute_file
import settings
import os


def get_sql_file_path(name):
    return os.path.join(settings.SQLDIR, name)


def confirm(msg):
    return raw_input("{} [y/n] ".format(msg)).lower() == 'y'


if not confirm("This will wipe any data in the database. Continue?"):
    print("Aborting.")
else:
    print execute_file(get_sql_file_path('data_model.sql'))
