#!/usr/bin/env python

from flask.ext.migrate import MigrateCommand

from patch_path import patch_path
patch_path()

from flask.ext.script import Manager, Server
from flask.ext.script.commands import ShowUrls, Clean
from mobile_endpoint import create_app
from mobile_endpoint.models import db, FormData, CaseData, CaseIndex, Synclog, OwnershipCleanlinessFlag
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase, MongoSynclog

app = create_app()

manager = Manager(app)
manager.add_command("runserver", Server())
manager.add_command("show-urls", ShowUrls())
manager.add_command("clean", Clean())
manager.add_command('db', MigrateCommand)


@manager.shell
def make_shell_context():
    """ Creates a python REPL with several default imports
        in the context of the app
    """

    context = dict(app=app, db=db)
    for class_ in [FormData, CaseData, CaseIndex, Synclog, OwnershipCleanlinessFlag]:
        context[class_.__name__] = class_
    return context

@manager.command
def syncmongo():
    MongoForm.ensure_indexes()
    MongoCase.ensure_indexes()
    MongoSynclog.ensure_indexes()

if __name__ == "__main__":
    manager.run()
