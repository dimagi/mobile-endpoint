from flask.blueprints import Blueprint

ota_mod = Blueprint('receiver', __name__)

from receiver import form_receiver
from restore import ota_restore
