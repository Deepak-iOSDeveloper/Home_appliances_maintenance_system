"""Troubleshooter Views"""
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import TechnicalManual, ChatSession, Message
from .serializers import (
    TechnicalManualSerializer,
    ChatSessionSerializer,
    ChatSessionListSerializer,
    CreateSessionSerializer,
    MessageSerializer,
)


class TechnicalManualViewSet(viewsets.ModelViewSet):
    """Browse and upload technical manuals."""
    serializer_class = TechnicalManualSerializer
    queryset = TechnicalManual.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        device_type = self.request.query_params.get('device_type')
        brand = self.request.query_params.get('brand')
        if device_type:
            qs = qs.filter(device_type__icontains=device_type)
        if brand:
            qs = qs.filter(brand__icontains=brand)
        return qs

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """Upload and index a PDF manual."""
        print(f"DEBUG: Upload received. Files: {request.FILES.keys()}")
        file = request.FILES.get('file')
        if not file:
            return Response({'error': f'No file uploaded. Keys found: {list(request.FILES.keys())}'}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"DEBUG: Filename: {file.name}")
        if not file.name.lower().endswith('.pdf'):
            return Response({'error': 'Only PDF files are supported currently'}, status=status.HTTP_400_BAD_REQUEST)

        import pdfplumber
        import io
        import numpy as np
        import pypdfium2 as pdfium
        import easyocr

        try:
            file_bytes = file.read()
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                print(f"DEBUG: PDF Pages: {len(pdf.pages)}")
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            
            print(f"DEBUG: Extracted text length: {len(full_text)}")
            
            # OCR FALLBACK: If no text extracted, use EasyOCR
            if not full_text.strip():
                print("DEBUG: Scanned PDF detected. Starting OCR...")
                reader = easyocr.Reader(['en'])
                pdf_doc = pdfium.PdfDocument(io.BytesIO(file_bytes))
                
                # Limit to first 20 pages for performance
                max_pages = min(len(pdf_doc), 20)
                for i in range(max_pages):
                    print(f"DEBUG: OCR Processing Page {i+1}/{max_pages}")
                    page = pdf_doc[i]
                    bitmap = page.render(scale=2)
                    pil_image = bitmap.to_pil()
                    # Perform OCR
                    results = reader.readtext(np.array(pil_image), detail=0)
                    full_text += " ".join(results) + "\n"
                
                print(f"DEBUG: OCR Complete. Extracted length: {len(full_text)}")

            if not full_text.strip():
                return Response({'error': 'No text could be extracted even with OCR. The PDF might be corrupted or in an unsupported format.'}, status=status.HTTP_400_BAD_REQUEST)

            # Chunking: ~1200 chars with overlap
            chunk_size = 1200
            overlap = 200
            chunks = []
            for i in range(0, len(full_text), chunk_size - overlap):
                chunks.append(full_text[i:i + chunk_size])

            filename = file.name.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
            
            manual_objs = []
            for idx, chunk in enumerate(chunks):
                manual_objs.append(TechnicalManual(
                    device_type='Uploaded',
                    brand='Manual',
                    title=f"{filename} (Part {idx + 1})",
                    content=chunk,
                    chunk_index=idx
                ))
            
            TechnicalManual.objects.bulk_create(manual_objs)
            
            return Response({
                'message': f'Manual "{file.name}" indexed successfully!',
                'chunks_created': len(manual_objs)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'PDF processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """Manage chat sessions."""

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatSessionListSerializer
        if self.action == 'create':
            return CreateSessionSerializer
        return ChatSessionSerializer

    def get_queryset(self):
        return ChatSession.objects.prefetch_related('messages').all()

    def create(self, request, *args, **kwargs):
        """Create a new chat session."""
        serializer = CreateSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = ChatSession.objects.create(
            session_id=str(uuid.uuid4()),
            title=serializer.validated_data.get('title', 'New Session'),
            device_context=serializer.validated_data.get('device_context', {}),
        )

        return Response(
            ChatSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='messages')
    def messages(self, request, pk=None):
        """Get all messages for a session."""
        session = self.get_object()
        messages = session.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
