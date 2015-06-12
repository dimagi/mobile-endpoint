from utils import execute_file, confirm
import settings
import os


def get_sql_file_path(name):
    return os.path.join(settings.SQLDIR, name)


if not confirm("This will wipe any data in the database. Continue?"):
    print("Aborting.")
else:
    print execute_file(get_sql_file_path('data_model.sql'))
