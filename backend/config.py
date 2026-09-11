import os


class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.environ.get('MYSQL_USER', 'regenwormen')}:"
        f"{os.environ.get('MYSQL_PASSWORD', 'regenwormen')}@"
        f"{os.environ.get('MYSQL_HOST', 'mysql')}:3306/"
        f"{os.environ.get('MYSQL_DATABASE', 'regenwormen')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 12


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True
    JWT_SECRET_KEY = "test-secret"
