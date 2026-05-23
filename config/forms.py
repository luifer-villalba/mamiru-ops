from unfold.forms import AuthenticationForm


class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "Usuario o correo"
