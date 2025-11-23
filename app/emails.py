from typing import Any, Dict
import os

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

from djoser import email
import resend

from .models import OTPCode

# Initialize Resend API key
resend.api_key = os.environ.get('RESEND_API_KEY', 're_3HrFPxTW_3PZssqZHbW3wNViQmwuiZund')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'Acme <no-reply@gnikcurt.dpdns.org>')


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

    def send(self, to=None, *args, **kwargs) -> None:
        """Override send method to use Resend instead of Django email backend"""
        context = self.get_context_data()
        html_body = render_to_string(self.template_name, context)
        subject = render_to_string('emails/activation_subject.txt', context).strip()
        
        # Get recipient email - use 'to' parameter if provided, otherwise get from user context
        if to:
            to_email = to[0] if isinstance(to, list) else to
        else:
            user = context.get('user')
            if not user or not hasattr(user, 'email'):
                raise ValueError("No recipient email address found in user context")
            to_email = user.email
        
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [to_email] if not isinstance(to_email, list) else to_email,  # Email from user input in frontend
            "subject": subject,
            "html": html_body,
        }
        
        try:
            response = resend.Emails.send(params)
            return response
        except Exception as e:
            # Log error but don't fail silently
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send activation email via Resend: {str(e)}")
            raise


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

        # Use Resend to send email
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [self.otp.user.email],  # Email from user input in frontend
            "subject": subject,
            "html": html_body,
        }
        
        try:
            response = resend.Emails.send(params)
            return response
        except Exception as e:
            # Log error but don't fail silently
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send OTP email via Resend: {str(e)}")
            raise
