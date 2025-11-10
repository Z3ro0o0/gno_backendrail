from typing import Any, Dict

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

from djoser import email

from .models import OTPCode


class CustomActivationEmail(email.ActivationEmail):
    template_name = 'emails/activation_email.html'

    def get_context_data(self) -> Dict[str, Any]:
        context = super().get_context_data()
        context.update(
            site_name=settings.DJOSER.get('SITE_NAME', 'Ong Trucking'),
            support_email=getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL),
            current_year=timezone.now().year,
        )
        return context

    def render(self) -> None:
        context = self.get_context_data()
        html_body = render_to_string(self.template_name, context)
        text_body = strip_tags(html_body)

        self.body = text_body
        if self.attach_alternative:  # pragma: no cover - base class handles this
            self.attach_alternative(html_body, 'text/html')
        else:
            self.extra_headers.setdefault('Content-Type', 'text/html; charset=utf-8')
            self.body = html_body

        self.subject = render_to_string('emails/activation_subject.txt', context).strip()


class OTPEmail:
    template_name = 'emails/otp_email.html'
    subject_template_name = 'emails/otp_subject.txt'

    def __init__(self, otp: OTPCode) -> None:
        self.otp = otp

    def send(self) -> None:
        context = {
            'user': self.otp.user,
            'code': self.otp.code,
            'site_name': settings.DJOSER.get('SITE_NAME', 'Ong Trucking'),
            'expires_at': self.otp.expires_at,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL),
            'current_year': timezone.now().year,
        }
        html_body = render_to_string(self.template_name, context)
        text_body = strip_tags(html_body)
        subject = render_to_string(self.subject_template_name, context).strip()

        from django.core.mail import EmailMultiAlternatives

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[self.otp.user.email],
        )
        email_message.attach_alternative(html_body, 'text/html')
        email_message.send()
