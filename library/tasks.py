from celery import shared_task
from .models import Loan
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings

@shared_task
def send_loan_notification(self, loan_id):
    try:
        loan = Loan.objects.select_for_update('member__user','book').get(id=loan_id)
        member_email = loan.member.user.email
        username=loan.member.user.username
        book_title = loan.book.title

        if not member_email:
            return "No email found for user"
        send_mail(
            subject='Book Loaned Successfully',
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )

        return f"Email sent to {member_email}"
    except Loan.DoesNotExist:
        pass

    #NEW TASK:OverDue loands checker:
    @shared_task(bind=True, autoretry_for=(Exception,),retry_backoff=5,retry_kwargs={'max_retries':3})
    def check_overdue_loans(self):
        now = timezone.now()

        overdue_loans = Loan.objects.select_related('member__user','book').filter(
            returned = False,
            due_date__lt=now
        )

        for loan in overdue_loans:
            member_email = loan.member.user.email
            username = loan.member.user.username
            book_title=loan.book.title

            if not member_email:
                continue

            send_mail(
                subject='Overdue Book Remainder',
                message=(
                    f'Hello {username},\n\n'
                    f'The book "{book_title} is overdue.\n'
                    f'Please return it as soon as possible.\n\n'
                    f'thank you.'
                ),

                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[member_email],
                fail_silently=False,
            )

            return f"Processed{overdue_loans.count()} overdue loans"

