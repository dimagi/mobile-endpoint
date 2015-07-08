from __future__ import print_function
import os
import random
import requests
from uuid import uuid4
import settings


POST_URL = "http://{host}:{port}/a/{domain}/receiver/{app_id}/".format(
    host=settings.HQ_HOST,
    port=settings.HQ_PORT,
    domain=settings.DOMAIN,
    app_id=settings.HQ_APP_ID
)


def post_form(form):
    requests.post(POST_URL, files={"xml_submission_file": form})


def load_data(scale):
    """
    * Load `scale` * settings.SCALE_FACTOR forms.
    * Select settings.FORM_CASE_RATIO forms to also have cases.
    * For settings.NEW_UPDATE_CASE_RATIO of those forms simulate a case update
    * For the rest of the forms load a single case for each form.
    * Make it a child case of an existing case for settings.CHILD_CASE_RATIO of the cases.
    """
    # TODO: Make this fast (while maintaining genericness) (might not be possible)

    scale_factor = settings.SCALE_FACTOR

    with open(os.path.join(settings.BASEDIR, 'forms', 'create.xml')) as f:
        create_case_form = f.read()
    with open(os.path.join(settings.BASEDIR, 'forms', 'nocase.xml')) as f:
        no_case_form = f.read()

    for i in xrange(scale * scale_factor):
        # TODO: Make requests in parallel
        has_case = random.random() < settings.FORM_CASE_RATIO
        if has_case:
            form = create_case_form
        else:
            form = no_case_form
        form = create_case_form.replace("%%_case_id%%", uuid4().hex).\
            replace("%%_user_id%%", settings.USER_ID).\
            replace("%%_username%%", settings.USERNAME).\
            replace("%%_form_instance_id%%", uuid4().hex)
        post_form(form)
