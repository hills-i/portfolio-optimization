from flask import Blueprint, render_template, jsonify, session, request, redirect, url_for
from flask_babel import get_locale

# メインルート用のブループリント
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """デフォルトルート - 英語にリダイレクト"""
    return redirect(url_for('main.index_lang', lang='en'))

@main_bp.route('/<lang>/')
def index_lang(lang):
    """言語付きメインページ"""
    if lang not in ['en', 'ja']:
        return redirect(url_for('main.index_lang', lang='en'))
    
    session['language'] = lang
    return render_template('index.html', lang=lang)

@main_bp.route('/<lang>/results')
def results_lang(lang):
    """言語付き結果表示ページ"""
    if lang not in ['en', 'ja']:
        return redirect(url_for('main.results_lang', lang='en'))
    
    session['language'] = lang
    return render_template('results.html', lang=lang)

@main_bp.route('/results')
def results():
    """結果表示ページ - 英語にリダイレクト"""
    return redirect(url_for('main.results_lang', lang='en'))