#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通知服务模块
支持邮件、钉钉、企业微信等通知方式
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from datetime import datetime


class NotificationService:
    """通知服务类"""
    
    def __init__(self, app=None):
        self.app = app
        self.mail_config = {}
        self.dingtalk_webhook = None
        self.wecom_webhook = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化配置"""
        self.mail_config = {
            'host': app.config.get('MAIL_SERVER', 'smtp.qq.com'),
            'port': app.config.get('MAIL_PORT', 465),
            'user': app.config.get('MAIL_USERNAME', ''),
            'password': app.config.get('MAIL_PASSWORD', ''),
            'use_ssl': app.config.get('MAIL_USE_SSL', True),
            'sender': app.config.get('MAIL_DEFAULT_SENDER', '')
        }
        self.dingtalk_webhook = app.config.get('DINGTALK_WEBHOOK', '')
        self.wecom_webhook = app.config.get('WECOM_WEBHOOK', '')
    
    def send_email(self, to_list, subject, content, html=False):
        """
        发送邮件通知
        
        Args:
            to_list: 收件人列表
            subject: 邮件主题
            content: 邮件内容
            html: 是否为HTML格式
        
        Returns:
            bool: 是否发送成功
        """
        if not self.mail_config.get('user') or not self.mail_config.get('password'):
            print("邮件配置不完整，跳过发送")
            return False
        
        try:
            msg = MIMEMultipart('alternative') if html else MIMEText(content, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = self.mail_config['sender'] or self.mail_config['user']
            msg['To'] = ', '.join(to_list) if isinstance(to_list, list) else to_list
            
            if html:
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
                msg.attach(MIMEText(content, 'html', 'utf-8'))
            
            if self.mail_config['use_ssl']:
                smtp = smtplib.SMTP_SSL(self.mail_config['host'], self.mail_config['port'])
            else:
                smtp = smtplib.SMTP(self.mail_config['host'], self.mail_config['port'])
                smtp.starttls()
            
            smtp.login(self.mail_config['user'], self.mail_config['password'])
            smtp.sendmail(self.mail_config['user'], to_list if isinstance(to_list, list) else [to_list], msg.as_string())
            smtp.quit()
            
            print(f"邮件发送成功: {to_list}")
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    def send_dingtalk(self, title, content, at_mobiles=None, at_all=False):
        """
        发送钉钉机器人通知
        
        Args:
            title: 消息标题
            content: 消息内容
            at_mobiles: @的手机号列表
            at_all: 是否@所有人
        
        Returns:
            bool: 是否发送成功
        """
        if not self.dingtalk_webhook:
            print("钉钉Webhook未配置，跳过发送")
            return False
        
        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"### {title}\n\n{content}"
                },
                "at": {
                    "atMobiles": at_mobiles or [],
                    "isAtAll": at_all
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.dingtalk_webhook,
                data=json.dumps(data),
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            if result.get('errcode') == 0:
                print("钉钉通知发送成功")
                return True
            else:
                print(f"钉钉通知发送失败: {result}")
                return False
                
        except Exception as e:
            print(f"钉钉通知发送异常: {e}")
            return False
    
    def send_wecom(self, title, content):
        """
        发送企业微信机器人通知
        
        Args:
            title: 消息标题
            content: 消息内容
        
        Returns:
            bool: 是否发送成功
        """
        if not self.wecom_webhook:
            print("企业微信Webhook未配置，跳过发送")
            return False
        
        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {title}\n\n{content}"
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.wecom_webhook,
                data=json.dumps(data),
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            if result.get('errcode') == 0:
                print("企业微信通知发送成功")
                return True
            else:
                print(f"企业微信通知发送失败: {result}")
                return False
                
        except Exception as e:
            print(f"企业微信通知发送异常: {e}")
            return False
    
    def send_alarm_notification(self, alarm, channels=None):
        """
        发送告警通知
        
        Args:
            alarm: 告警对象
            channels: 通知渠道列表 ['email', 'dingtalk', 'wecom']
        
        Returns:
            dict: 各渠道发送结果
        """
        if channels is None:
            channels = ['email', 'dingtalk']
        
        # 构建告警内容
        level_text = {'critical': '严重', 'warning': '警告', 'info': '提示'}.get(alarm.level, '未知')
        title = f"【{level_text}】IoT设备告警 - {alarm.device_name}"
        
        content = f"""
**告警级别**: {level_text}
**告警类型**: {alarm.alarm_type}
**设备名称**: {alarm.device_name}
**告警内容**: {alarm.content}
**触发时间**: {alarm.triggered_at.strftime('%Y-%m-%d %H:%M:%S') if alarm.triggered_at else '未知'}
**当前值**: {alarm.current_value or '未知'}

请及时处理！
"""
        
        results = {}
        
        if 'email' in channels:
            results['email'] = self.send_email(
                to_list=['admin@example.com'],  # 可从配置读取
                subject=title,
                content=content
            )
        
        if 'dingtalk' in channels:
            results['dingtalk'] = self.send_dingtalk(title, content)
        
        if 'wecom' in channels:
            results['wecom'] = self.send_wecom(title, content)
        
        return results


# 全局通知服务实例
notification_service = NotificationService()


def init_notification_service(app):
    """初始化通知服务"""
    notification_service.init_app(app)
    return notification_service
