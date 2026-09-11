from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, jwt, socketio


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)

    from auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from stats.routes import stats_bp
    app.register_blueprint(stats_bp, url_prefix="/api")

    from game import manager
    manager.init_app(app)

    from game.socket_handlers import register_handlers
    register_handlers(socketio)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    # allow_unsafe_werkzeug=True: required because flask-socketio's threading
    # async_mode refuses to start when stdin is not a tty (e.g. inside a
    # Docker container run without -it), which is how this dev service runs
    # under `docker compose up`. This is a dev-mode container; a real
    # production deployment would use a WSGI/ASGI server instead.
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
