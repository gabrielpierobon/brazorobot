from flask import Blueprint

# Create a new blueprint
grubbstest_bp = Blueprint('grubbstest', __name__)

# Import your views or routes
from . import views
