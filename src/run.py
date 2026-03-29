from app import create_app
import os

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(
        debug=os.environ.get('DEBUG', 'true').lower() == 'true',
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
