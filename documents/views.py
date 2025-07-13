import PyPDF2
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import FileResponse
from rank_bm25 import BM25Okapi
import nltk
import numpy as np
nltk.download('punkt')

from .models import Document
from .serializers import DocumentUploadSerializer

class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for document management
    """
    queryset = Document.objects.all()
    serializer_class = DocumentUploadSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Extract text from PDF
        file = self.request.data.get('file')
        pdf_reader = PyPDF2.PdfReader(file)
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text()
        
        # Save document with extracted text
        serializer.save(
            user=self.request.user, 
            filename=file.name, 
            extracted_text=extracted_text
        )
        
        return super().perform_create(serializer)
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """
        Handle the document upload
        """
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            # Perform document creation with extracted text
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def search(self, request):
        """
        Search documents using BM25 algorithm
        """
        query = request.query_params.get('query', '')
        
        # Fetch all documents for the current user
        user_documents = Document.objects.filter(user=request.user)
        
        # Prepare corpus and tokenization
        corpus = [nltk.word_tokenize(doc.extracted_text.lower()) for doc in user_documents]
        bm25 = BM25Okapi(corpus)
        
        # Tokenize query
        tokenized_query = nltk.word_tokenize(query.lower())
        
        # Get document scores
        scores = bm25.get_scores(tokenized_query)
        scores = np.abs(scores)

        print(scores)
        
        # Create results with metadata
        results = []
        for doc, score in zip(user_documents, scores):
            if score > 0:
                results.append({
                    'document_id': doc.id,
                    'filename': doc.filename,
                    'matched_text': doc.extracted_text[:200],  # First 200 chars as snippet
                    'score': score
                })
        
        # Sort results by score in descending order
        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:10]

        
        return Response(results)

    @action(detail=True, methods=['GET'])
    def retrieve_file(self, request, pk=None):
        """
        Retrieve PDF file
        """
        document = self.get_object()
        
        # Ensure user owns the document
        if document.user != request.user:
            return Response({'message': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        response = FileResponse(
            document.file, 
            as_attachment=True, 
            filename=document.filename
        )
        return response