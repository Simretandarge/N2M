from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from content.models import NewsletterIssue, NewsletterSubscriber
from content.views import (
    _broadcast_newsletter_emails,
    _digest_items_from_newsletter_issues,
    _render_newsletter_digest_email,
    _site_public_base_url,
)


class Command(BaseCommand):
    help = "Send all posted newsletters during configured weekly send window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore weekday/time window and send posted newsletters now.",
        )

    def handle(self, *args, **options):
        tz_name = getattr(settings, "WEEKLY_DIGEST_TIMEZONE", "Africa/Addis_Ababa")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz_name = "UTC"
            tz = ZoneInfo("UTC")
        weekday = max(0, min(6, int(getattr(settings, "WEEKLY_DIGEST_SEND_WEEKDAY", 4))))
        hour = max(0, min(23, int(getattr(settings, "WEEKLY_DIGEST_SEND_HOUR", 20))))
        minute = max(0, min(59, int(getattr(settings, "WEEKLY_DIGEST_SEND_MINUTE", 0))))
        window = max(1, int(getattr(settings, "WEEKLY_DIGEST_SEND_WINDOW_MINUTES", 120)))

        now_utc = timezone.now()
        local_now = timezone.localtime(now_utc, tz)
        current_minutes = local_now.hour * 60 + local_now.minute
        target_minutes = hour * 60 + minute
        in_window = local_now.weekday() == weekday and abs(current_minutes - target_minutes) <= window

        if not options["force"] and not in_window:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped: outside send window. Local time={local_now.strftime('%A %H:%M')} ({tz_name}), "
                    f"target weekday={weekday}, time={hour:02d}:{minute:02d}, window=±{window}m"
                )
            )
            return

        max_items = max(1, int(getattr(settings, "WEEKLY_DIGEST_MAX_ITEMS", 12)))
        posted_issues = list(
            NewsletterIssue.objects.filter(status=NewsletterIssue.STATUS_POSTED)
            .annotate(
                like_count=Count("likes", distinct=True),
                bookmark_count=Count("bookmarked_by", distinct=True),
            )
            .order_by("-like_count", "-bookmark_count", "-posted_at", "-created_at")[:max_items]
        )
        if not posted_issues:
            self.stdout.write(self.style.WARNING("No posted newsletters to send."))
            return
        if not NewsletterSubscriber.objects.exists():
            self.stdout.write(self.style.WARNING("No newsletter subscribers."))
            return

        base = _site_public_base_url().rstrip("/")
        items = _digest_items_from_newsletter_issues(
            posted_issues,
            lambda o: f"{base}{o.get_absolute_url()}",
        )
        site_name = getattr(settings, "SITE_NAME", "Next 251 Media")
        date_label = timezone.now().strftime("%d %b %Y")
        n = len(posted_issues)
        digest_intro = (
            f"Here are {n} newsletter topic{'s' if n != 1 else ''} in one message. "
            "Click a title to read the full issue on our site."
        )
        html = _render_newsletter_digest_email(
            site_name,
            date_label,
            items,
            digest_intro=digest_intro,
            subscription_note="newsletter topics",
            unsubscribe_hint=f"{base}{reverse('content:home')}#newsletter",
        )
        subject = f"{site_name} — {n} newsletter topic{'s' if n != 1 else ''} ({date_label})"
        sent, failed, first_err = _broadcast_newsletter_emails(subject, html, is_html=True)
        if sent > 0:
            now = timezone.now()
            for issue in posted_issues:
                issue.status = NewsletterIssue.STATUS_SENT
                issue.sent_at = now
                if not issue.posted_at:
                    issue.posted_at = now
                issue.save(update_fields=["status", "sent_at", "posted_at"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sent one roundup email to {sent} subscriber(s) with {n} topic link(s)."
                )
            )
            if failed:
                self.stdout.write(self.style.WARNING(f"{failed} delivery failure(s). {first_err or ''}"))
        else:
            self.stdout.write(
                self.style.ERROR(first_err or "No emails delivered. Check SMTP and subscribers.")
            )
