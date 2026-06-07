from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile_no = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    show_email_on_profile = models.BooleanField(default=True)  
    make_profile_private = models.BooleanField(default=False)  # 👈 Add this
    is_private = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username