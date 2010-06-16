# python
import os
import codecs

# django
from django import forms
from django.core.files import File
from django.conf import settings

# local
from theme_editor.utils import archive_file

class FileForm(forms.Form):
    content = forms.CharField(label="Content",
                           widget=forms.Textarea(attrs={'rows':26, 'cols':73}),
                           max_length=100000
                           )
    rf_path = forms.CharField(widget=forms.HiddenInput())
    
    def save(self, request, file_relative_path):
        content = self.cleaned_data["content"]
        file_path = (os.path.join(settings.THEME_ROOT, file_relative_path)).replace("\\", "/")
        if os.path.isfile(file_path) and content <> "":
            archive_file(request, file_relative_path)
            f = codecs.open(file_path, 'w', 'utf-8', 'replace')
            file = File(f)
            file.write(content)
            file.close()
            return True
        else:
            return False
        