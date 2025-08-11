from flask import Blueprint, render_template, jsonify

# メインルート用のブループリント
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@main_bp.route('/results')
def results():
    """結果表示ページ"""
    return render_template('results.html')