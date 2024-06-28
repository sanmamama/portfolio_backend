from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        return f"http://127.0.0.1:3000/postter/confirm/?key={emailconfirmation.key}"
