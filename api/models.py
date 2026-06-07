from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import os

GENDER_CHOICES = [
    ('MEN', 'Men'),
    ('WOMEN', 'Women'),
]

PROFILE_CHOICES = [
    ('front', 'Front'),
    ('full', 'Full'),
    ('additional', 'Additional'),
    ('side', 'Side'),
    ('back', 'Back'),
]

CATEGORY_CHOICES_MEN = [
    ('Denim', 'Denim'),
    ('Jackets_Vests', 'Jackets & Vests'),
    ('Pants', 'Pants'),
    ('Shirts_Polos', 'Shirts & Polos'),
    ('Shorts', 'Shorts'),
    ('Suiting', 'Suiting'),
    ('Sweaters', 'Sweaters'),
    ('Sweatshirts', 'Sweatshirts'),
    ('Tees_Tanks', 'Tees & Tanks'),
]

CATEGORY_CHOICES_WOMEN = [
    ('Blouses_Shirts', 'Blouses & Shirts'),
    ('Cardigans', 'Cardigans'),
    ('Denim', 'Denim'),
    ('Dresses', 'Dresses'),
    ('Graphic_Tees', 'Graphic Tees'),
    ('Jackets_Coats', 'Jackets & Coats'),
    ('Leggings', 'Leggings'),
    ('Pants', 'Pants'),
    ('Rompers_Jumpsuits', 'Rompers & Jumpsuits'),
    ('Shorts', 'Shorts'),
    ('Skirts', 'Skirts'),
    ('Sweaters', 'Sweaters'),
    ('Sweatshirts_Hoodies', 'Sweatshirts & Hoodies'),
    ('Tees_Tanks', 'Tees & Tanks'),
]

def custom_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{instance.gender}-{instance.category}-{instance.profile}-{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join("uploads", filename)

class Upload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    category = models.CharField(max_length=50)
    profile = models.CharField(max_length=20, choices=PROFILE_CHOICES)
    image = models.ImageField(upload_to=custom_upload_to)
    same_profile = models.BooleanField(default=False)
    is_multiple = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.gender} - {self.category} - {self.profile} - {self.image.url}"

    def get_category_choices(self):
        return CATEGORY_CHOICES_MEN if self.gender == 'MEN' else CATEGORY_CHOICES_WOMEN


class Board(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='boards')
    created_at = models.DateTimeField(default=timezone.now)
    pinned = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    is_private = models.BooleanField(default=True)

    # soft-delete
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s {self.name}"

    @staticmethod
    def get_default_board(user):
        board, _ = Board.objects.get_or_create(
            user=user,
            name="My Saves",
            defaults={'description': 'Your default board for saved items'}
        )
        return board

    @property
    def image_count(self):
        return self.inspos.filter(is_deleted=False).count()

    def get_preview_images(self, limit=4):
        return self.inspos.filter(is_deleted=False).order_by('-saved_at')[:limit]


class Inspo(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='inspos')
    image_url = models.URLField()
    saved_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)

    # soft-delete
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.board.name} - {self.image_url}"

    @property
    def aspect_ratio(self):
        if self.image_width and self.image_height:
            return self.image_width / self.image_height
        return 1

class Image(models.Model):
    image_url = models.URLField()