"""
国际化路由
Internationalization Routes
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from services.i18n_service import I18nService, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

i18n_bp = Blueprint('i18n', __name__, url_prefix='/api/i18n')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


@i18n_bp.route('/languages', methods=['GET'])
def get_languages():
    """获取支持的語言列表"""
    return jsonify({
        'languages': [
            {'code': code, 'name': name}
            for code, name in SUPPORTED_LANGUAGES.items()
        ],
        'default': DEFAULT_LANGUAGE,
        'current': I18nService.get_current_language()
    })


@i18n_bp.route('/language', methods=['GET'])
def get_current_language():
    """获取当前语言"""
    return jsonify({
        'language': I18nService.get_current_language(),
        'language_name': SUPPORTED_LANGUAGES.get(
            I18nService.get_current_language(), 
            SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE]
        )
    })


@i18n_bp.route('/language', methods=['POST'])
def set_language():
    """设置当前语言"""
    data = request.get_json()
    
    if not data or 'language' not in data:
        return jsonify({'error': '缺少语言参数'}), 400
    
    language = data['language']
    
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({
            'error': f'不支持的语言: {language}',
            'supported': list(SUPPORTED_LANGUAGES.keys())
        }), 400
    
    success = I18nService.set_language(language)
    
    if success:
        return jsonify({
            'message': '语言设置成功',
            'language': language,
            'language_name': SUPPORTED_LANGUAGES[language]
        })
    else:
        return jsonify({'error': '语言设置失败'}), 500


@i18n_bp.route('/translations', methods=['GET'])
def get_translations():
    """获取翻译文本"""
    language = request.args.get('language') or I18nService.get_current_language()
    category = request.args.get('category')
    
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    translations = I18nService.get_all_translations(language)
    
    if category:
        translations = translations.get(category, {})
    
    return jsonify({
        'language': language,
        'translations': translations
    })


@i18n_bp.route('/translate', methods=['POST'])
def translate():
    """翻译单个文本"""
    data = request.get_json()
    
    if not data or 'key' not in data:
        return jsonify({'error': '缺少翻译键'}), 400
    
    key = data['key']
    language = data.get('language') or I18nService.get_current_language()
    params = data.get('params', {})
    
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    translation = I18nService.get_translation(key, language, **params)
    
    return jsonify({
        'key': key,
        'language': language,
        'translation': translation
    })


@i18n_bp.route('/translate/batch', methods=['POST'])
def translate_batch():
    """批量翻译文本"""
    data = request.get_json()
    
    if not data or 'keys' not in data:
        return jsonify({'error': '缺少翻译键列表'}), 400
    
    keys = data['keys']
    language = data.get('language') or I18nService.get_current_language()
    
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    translations = {}
    for key in keys:
        translations[key] = I18nService.get_translation(key, language)
    
    return jsonify({
        'language': language,
        'translations': translations
    })


@i18n_bp.route('/reload', methods=['POST'])
@login_required
def reload_translations():
    """重新加载翻译文件 (需要登录)"""
    language = request.args.get('language')
    
    I18nService.reload_translations(language)
    
    return jsonify({
        'message': '翻译缓存已清除',
        'language': language or 'all'
    })
