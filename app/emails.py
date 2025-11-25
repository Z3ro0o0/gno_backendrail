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
resend.api_key = os.environ.get('RESEND_API_KEY', 're_EEXw54RC_KwBw1XsD95UX35TzCZNU2jXB')
# Use Resend's default domain for testing, or set RESEND_FROM_EMAIL env var with a verified domain
# For production, you MUST verify your domain in Resend and use that domain
# IMPORTANT: Using "onboarding" instead of "no-reply" for better deliverability
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'Ong Trucking <onboarding@trucking.jeronpos.com>')

# Debug: Print the email being used (remove in production)
if os.environ.get('DEBUG_EMAIL', 'False').lower() == 'true':
    print(f"[DEBUG] Using RESEND_FROM_EMAIL: {RESEND_FROM_EMAIL}")


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
        text_body = strip_tags(html_body)
        subject = render_to_string('emails/activation_subject.txt', context).strip()
        
        # Get recipient email - use 'to' parameter if provided, otherwise get from user context
        if to:
            to_email = to[0] if isinstance(to, list) else to
        else:
            user = context.get('user')
            if not user or not hasattr(user, 'email'):
                raise ValueError("No recipient email address found in user context")
            to_email = user.email
        
        # Get support email for reply-to
        support_email = context.get('support_email', 'support@ongtrucking.com')
        
        # Clean up text body - remove extra whitespace and format better
        text_body_clean = '\n'.join(line.strip() for line in text_body.split('\n') if line.strip())
        
        # Extract domain from RESEND_FROM_EMAIL for consistency
        from_domain = RESEND_FROM_EMAIL.split('@')[1].split('>')[0] if '@' in RESEND_FROM_EMAIL else 'jeronpos.com'
        
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [to_email] if not isinstance(to_email, list) else to_email,
            "subject": subject,
            "html": html_body,
            "text": text_body_clean,  # Clean plain text version
            "reply_to": support_email,  # Add reply-to header
            "headers": {
                "X-Entity-Ref-ID": f"activation-{context.get('user', {}).id if context.get('user') else 'unknown'}",
                "List-Unsubscribe": f"<mailto:{support_email}?subject=unsubscribe>",
                "X-Mailer": "Ong Trucking Platform",
            },
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
        support_email = context.get('support_email', 'support@ongtrucking.com')
        
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [self.otp.user.email],
            "subject": subject,
            "html": html_body,
            "text": text_body,  # Add plain text version
            "reply_to": support_email,  # Add reply-to header
            "headers": {
                "X-Entity-Ref-ID": f"otp-{self.otp.user.id}",
            },
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
