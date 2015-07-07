#!/usr/bin/env python

import os
import sys

from flask.ext.migrate import MigrateCommand


def _set_source_root_parent(source_root_parent):
    """
    add everything under `source_root_parent` to the list of source roots
    e.g. if you call this with param 'submodules'
    and you have the file structure

    project/
        submodules/
            foo-src/
                foo/
            bar-src/
                bar/

    (where foo and bar are python modules)
    then foo and bar would become top-level importable

    """
    filedir = os.path.dirname(__file__)
    submodules_list = os.listdir(os.path.join(filedir, source_root_parent))
    for d in submodules_list:
        if d == "__init__.py" or d == '.' or d == '..':
            continue
        sys.path.insert(1, os.path.join(filedir, source_root_parent, d))

    sys.path.append(os.path.join(filedir, source_root_parent))

_set_source_root_parent('submodules')

from flask.ext.script import Manager, Server
from flask.ext.script.commands import ShowUrls, Clean
from mobile_endpoint import create_app
from mobile_endpoint.models import db, FormData, CaseData, CaseIndex

app = create_app()

manager = Manager(app)
manager.add_command("server", Server())
manager.add_command("show-urls", ShowUrls())
manager.add_command("clean", Clean())
manager.add_command('db', MigrateCommand)


@manager.shell
def make_shell_context():
    """ Creates a python REPL with several default imports
        in the context of the app
    """

    return dict(app=app, db=db, FormData=FormData, CaseData=CaseData, CaseIndex=CaseIndex)


if __name__ == "__main__":
    manager.run()
