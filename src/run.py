import os
from app import create_app

def _env_flag(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() == 'true'

app = create_app(os.environ.get('APP_ENV', 'development'))

if __name__ == '__main__':
    app.run(
        debug=_env_flag('DEBUG', app.config.get('DEBUG', False)),
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
