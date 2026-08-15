from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/version")
    def version():
        return {"version": "0.1.0"}

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
