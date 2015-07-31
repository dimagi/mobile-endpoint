import os
from patch_path import patch_path
patch_path()

from mobile_endpoint import create_app

# Optionally, set up psycopg2 & SQLAlchemy to be greenlet-friendly.
# Note: psycogreen does not really monkey patch psycopg2 in the
# manner that gevent monkey patches socket.
#
if "PSYCOGREEN" in os.environ:

    # Do our monkey patching
    #
    from restkit.session import set_session
    set_session("gevent")
    from gevent.monkey import patch_all
    patch_all()
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()


app = create_app()

if __name__ == '__main__':
    app.run()
