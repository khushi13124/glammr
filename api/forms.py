from django import forms
from .models import Upload, Board

class UploadForm(forms.ModelForm):
    class Meta:
        model = Upload
        fields = ['gender', 'category', 'profile', 'image', 'same_profile']
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-control text-uppercase'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'profile': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'same_profile': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gender'].label = "GENDER"
        self.fields['category'].label = "CATEGORY"
        self.fields['profile'].label = "PROFILE"

class BoardForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ['name']