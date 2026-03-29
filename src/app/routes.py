from flask import Blueprint, render_template, jsonify, session, request, redirect, url_for
from flask_babel import get_locale

# Blueprint for the main routes.
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Default route that redirects to English."""
    return redirect(url_for('main.index_lang', lang='en'))

@main_bp.route('/<lang>/')
def index_lang(lang):
    """Main page with an explicit language code."""
    if lang not in ['en', 'ja']:
        return redirect(url_for('main.index_lang', lang='en'))
    
    session['language'] = lang
    return render_template('index.html', lang=lang)
