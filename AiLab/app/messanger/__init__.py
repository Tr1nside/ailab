from flask import Blueprint

blueprint = Blueprint(
    "messanger_blueprint",
    __name__,
    url_prefix="",
    template_folder="templates",
    static_folder="static",
)
