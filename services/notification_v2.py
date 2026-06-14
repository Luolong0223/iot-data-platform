"""多渠道通知服务 - 邮件/钉钉/企业微信/Webhook/站内信"""
import json
import requests as http_requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import current_app

from models.database import db, NotificationLog, SystemMessage


def log_notification(user_id, channel, target, subject, content, status, error_msg=None):
    """记录通知日志"""
    try:
        log = NotificationLog(
            user_id=user_id,
            channel=channel,
            target=target,
            subject=subject[:255] if subject else None,
            content=content[:2000] if content else None,
            status=status,
            error_msg=error_msg[:500] if error_msg else None,
            sent_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f'[notification_log] 失败: {e}')


def send_email(to_addr, subject, content, html=False):
    """发送邮件"""
    try:
        from flask import current_app
        cfg = current_app.config
        if not cfg.get('MAIL_SERVER'):
            return False, '邮件未配置'

        msg = MIMEMultipart() if html else MIMEText(content, 'html' if html else 'plain', 'utf-8')
        msg['From'] = cfg.get('MAIL_DEFAULT_SENDER', 'iot@example.com')
        msg['To'] = to_addr
        msg['Subject'] = subject

        if html:
            msg.attach(MIMEText(content, 'html', 'utf-8'))

        if cfg.get('MAIL_USE_SSL'):
            smtp = smtplib.SMTP_SSL(cfg['MAIL_SERVER'], cfg.get('MAIL_PORT', 465), timeout=10)
        else:
            smtp = smtplib.SMTP(cfg['MAIL_SERVER'], cfg.get('MAIL_PORT', 25), timeout=10)
            if cfg.get('MAIL_USE_TLS'):
                smtp.starttls()

        smtp.login(cfg.get('MAIL_USERNAME'), cfg.get('MAIL_PASSWORD'))
        smtp.send_message(msg)
        smtp.quit()
        return True, None
    except Exception as e:
        return False, str(e)[:200]


def send_dingtalk(webhook, secret=None, title, content, msg_type='markdown'):
    """发送钉钉机器人消息

    msg_type: text / markdown / link / actionCard
    """
    try:
        if not webhook:
            return False, '钉钉 Webhook 未配置'

        # 加签逻辑
        if secret:
            import time, hmac, hashlib, base64, urllib.parse
            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode('utf-8')
            string_to_sign = f'{timestamp}\n{secret}'.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook = f'{webhook}&timestamp={timestamp}&sign={sign}'

        if msg_type == 'markdown':
            data = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': title,
                    'text': content
                }
            }
        elif msg_type == 'text':
            data = {
                'msgtype': 'text',
                'text': {'content': content}
            }
        elif msg_type == 'actionCard':
            data = {
                'msgtype': 'actionCard',
                'actionCard': {
                    'title': title,
                    'text': content,
                    'singleTitle': '查看详情',
                    'singleURL': 'https://example.com'
                }
            }
        else:
            data = {
                'msgtype': 'text',
                'text': {'content': f'{title}\n{content}'}
            }

        resp = http_requests.post(webhook, json=data, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            return True, None
        return False, f"errcode={result.get('errcode')}, errmsg={result.get('errmsg')}"
    except Exception as e:
        return False, str(e)[:200]


def send_wechat_work(webhook, content, mentioned=None):
    """发送企业微信机器人消息"""
    try:
        if not webhook:
            return False, '企业微信 Webhook 未配置'

        data = {
            'msgtype': 'markdown',
            'markdown': {
                'content': content
            }
        }
        if mentioned:
            data['markdown']['mentioned_list'] = mentioned if isinstance(mentioned, list) else [mentioned]

        resp = http_requests.post(webhook, json=data, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            return True, None
        return False, f"errcode={result.get('errcode')}, errmsg={result.get('errmsg')}"
    except Exception as e:
        return False, str(e)[:200]


def send_webhook(url, payload, headers=None, method='POST', timeout=10):
    """发送通用 Webhook"""
    try:
        if not url:
            return False, 'Webhook URL 未配置'
        headers = headers or {'Content-Type': 'application/json'}
        if method.upper() == 'POST':
            resp = http_requests.post(url, json=payload, headers=headers, timeout=timeout)
        else:
            resp = http_requests.get(url, params=payload, headers=headers, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return True, None
        return False, f'HTTP {resp.status_code}: {resp.text[:200]}'
    except Exception as e:
        return False, str(e)[:200]


def send_system_message(user_id, msg_type, title, content, level='info', ref_id=None, ref_type=None):
    """发送站内信"""
    try:
        msg = SystemMessage(
            user_id=user_id,
            type=msg_type,
            level=level,
            title=title[:200],
            content=content[:2000] if content else None,
            ref_id=ref_id,
            ref_type=ref_type
        )
        db.session.add(msg)
        db.session.commit()
        return True
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f'[system_msg] 失败: {e}')
        return False


def dispatch_notification(user_id, channels, subject, content, **kwargs):
    """根据配置多渠道分发通知

    channels: dict like {'email': 'a@b.com', 'dingtalk': 'webhook', 'system': True}
    """
    title = kwargs.get('title', subject)
    results = {}

    if channels.get('email'):
        email = channels['email']
        ok, err = send_email(email, subject, content, html=kwargs.get('html', True))
        results['email'] = {'success': ok, 'error': err}
        log_notification(user_id, 'email', email, subject, content, 'success' if ok else 'failed', err)

    if channels.get('dingtalk'):
        webhook = channels['dingtalk']
        secret = channels.get('dingtalk_secret')
        msg_type = channels.get('dingtalk_msgtype', 'markdown')
        ok, err = send_dingtalk(webhook, secret, title, content, msg_type)
        results['dingtalk'] = {'success': ok, 'error': err}
        log_notification(user_id, 'dingtalk', webhook[:120], subject, content, 'success' if ok else 'failed', err)

    if channels.get('wechat'):
        webhook = channels['wechat']
        ok, err = send_wechat_work(webhook, f'## {title}\n{content}', mentioned=channels.get('wechat_mentioned'))
        results['wechat'] = {'success': ok, 'error': err}
        log_notification(user_id, 'wechat', webhook[:120], subject, content, 'success' if ok else 'failed', err)

    if channels.get('webhook'):
        url = channels['webhook']
        ok, err = send_webhook(url, {'subject': subject, 'content': content, 'title': title})
        results['webhook'] = {'success': ok, 'error': err}
        log_notification(user_id, 'webhook', url[:120], subject, content, 'success' if ok else 'failed', err)

    if channels.get('system', True):
        ok = send_system_message(user_id, kwargs.get('msg_type', 'alarm'),
                                  title, content, level=kwargs.get('level', 'warning'),
                                  ref_id=kwargs.get('ref_id'), ref_type=kwargs.get('ref_type'))
        results['system'] = {'success': ok}

    return results
