from rest_framework import serializers
from .models import Document

class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for document upload
    """
    class Meta:
        model = Document
        fields = ['id', 'file', 'filename']
        read_only_fields = ['id']