"""
国际化服务
Internationalization (i18n) Service
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from functools import wraps
from flask import request, session, g

logger = logging.getLogger(__name__)

# 支持的語言列表
SUPPORTED_LANGUAGES = {
    'zh_CN': '简体中文',
    'en_US': 'English'
}

# 默认语言
DEFAULT_LANGUAGE = 'zh_CN'

# 翻译文件目录
TRANSLATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'translations')

# 翻译缓存
_translations_cache: Dict[str, Dict[str, Any]] = {}


class I18nService:
    """国际化服务"""
    
    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        """获取支持的語言列表"""
        return SUPPORTED_LANGUAGES.copy()
    
    @staticmethod
    def get_current_language() -> str:
        """获取当前语言"""
        # 优先从 session 获取
        if 'language' in session:
            lang = session['language']
            if lang in SUPPORTED_LANGUAGES:
                return lang
        
        # 其次从请求头获取
        accept_language = request.headers.get('Accept-Language', '')
        if accept_language:
            # 解析 Accept-Language 头
            for lang_part in accept_language.split(','):
                lang = lang_part.split(';')[0].strip()
                # 标准化语言代码
                if lang.startswith('zh'):
                    return 'zh_CN'
                elif lang.startswith('en'):
                    return 'en_US'
        
        return DEFAULT_LANGUAGE
    
    @staticmethod
    def set_language(language: str) -> bool:
        """设置当前语言"""
        if language not in SUPPORTED_LANGUAGES:
            return False
        
        session['language'] = language
        return True
    
    @staticmethod
    def load_translations(language: str) -> Dict[str, Any]:
        """加载翻译文件"""
        if language in _translations_cache:
            return _translations_cache[language]
        
        translations_file = os.path.join(TRANSLATIONS_DIR, language, 'messages.json')
        
        if not os.path.exists(translations_file):
            logger.warning(f"翻译文件不存在: {translations_file}")
            return {}
        
        try:
            with open(translations_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                _translations_cache[language] = translations
                return translations
        except Exception as e:
            logger.error(f"加载翻译文件失败: {translations_file}, 错误: {e}")
            return {}
    
    @staticmethod
    def get_translation(key: str, language: Optional[str] = None, **kwargs) -> str:
        """获取翻译文本
        
        Args:
            key: 翻译键，格式为 'category.key'，如 'common.success'
            language: 语言代码，不传则使用当前语言
            **kwargs: 格式化参数
        
        Returns:
            翻译后的文本
        """
        if language is None:
            language = I18nService.get_current_language()
        
        translations = I18nService.load_translations(language)
        
        # 解析键路径
        keys = key.split('.')
        value = translations
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # 找不到翻译，返回键名
                logger.warning(f"翻译键不存在: {key} (语言: {language})")
                return key
        
        # 格式化参数
        if isinstance(value, str) and kwargs:
            try:
                value = value.format(**kwargs)
            except Exception as e:
                logger.warning(f"翻译格式化失败: {key}, 参数: {kwargs}, 错误: {e}")
        
        return value if isinstance(value, str) else key
    
    @staticmethod
    def get_all_translations(language: Optional[str] = None) -> Dict[str, Any]:
        """获取所有翻译文本"""
        if language is None:
            language = I18nService.get_current_language()
        
        return I18nService.load_translations(language)
    
    @staticmethod
    def reload_translations(language: Optional[str] = None):
        """重新加载翻译文件"""
        if language:
            if language in _translations_cache:
                del _translations_cache[language]
        else:
            _translations_cache.clear()
        
        logger.info("翻译缓存已清除")


# 便捷函数
def t(key: str, **kwargs) -> str:
    """获取翻译文本的便捷函数"""
    return I18nService.get_translation(key, **kwargs)


def get_language() -> str:
    """获取当前语言的便捷函数"""
    return I18nService.get_current_language()


def set_language(language: str) -> bool:
    """设置当前语言的便捷函数"""
    return I18nService.set_language(language)


# Flask 请求钩子
def before_request_handler():
    """请求前处理函数，设置当前语言到 g 对象"""
    g.current_language = I18nService.get_current_language()


def after_request_handler(response):
    """请求后处理函数，添加语言相关响应头"""
    response.headers['Content-Language'] = g.get('current_language', DEFAULT_LANGUAGE)
    return response
