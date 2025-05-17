# models/media_processor.py
import os
import uuid
import shutil
from PIL import Image
import base64
import io
import numpy as np
import logging
from datetime import datetime
from config import IMAGE_UPLOAD_FOLDER, AUDIO_UPLOAD_FOLDER, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_AUDIO_EXTENSIONS

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MediaProcessor:
    @staticmethod
    def is_valid_image(filename):
        """Check if the file has an allowed image extension"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    
# models/media_processor.py
# Update the save_uploaded_file method:

    @staticmethod
    def save_uploaded_file(file, file_type):
        """Save an uploaded file to the appropriate folder"""
        if file is None:
            return None
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4().hex}"
        
        if file_type == "image":
            # Save image file
            if isinstance(file, str):
                # It's already a file path
                extension = file.split('.')[-1] if '.' in file else "jpg"
                filename = f"{filename}.{extension}"
                save_path = os.path.join(IMAGE_UPLOAD_FOLDER, filename)
                shutil.copy2(file, save_path)
            elif hasattr(file, 'name'):
                # For Gradio uploaded images
                extension = file.name.rsplit('.', 1)[1].lower() if '.' in file.name else "jpg"
                filename = f"{filename}.{extension}"
                save_path = os.path.join(IMAGE_UPLOAD_FOLDER, filename)
                shutil.copy2(file.name, save_path)
            elif isinstance(file, Image.Image):
                # If it's a PIL Image
                filename = f"{filename}.png"
                save_path = os.path.join(IMAGE_UPLOAD_FOLDER, filename)
                file.save(save_path)
            else:
                # If it's a direct file object or bytes
                extension = "jpg"
                filename = f"{filename}.{extension}"
                save_path = os.path.join(IMAGE_UPLOAD_FOLDER, filename)
                with open(save_path, 'wb') as f:
                    if isinstance(file, bytes):
                        f.write(file)
                    else:
                        f.write(file.read())
            
            return os.path.join("images", filename)
        
        elif file_type == "audio":
            # Save audio file
            if isinstance(file, str):
                # It's already a file path
                extension = file.split('.')[-1] if '.' in file else "wav"
                filename = f"{filename}.{extension}"
                save_path = os.path.join(AUDIO_UPLOAD_FOLDER, filename)
                shutil.copy2(file, save_path)
            elif hasattr(file, 'name'):
                # For Gradio uploaded audio
                extension = file.name.rsplit('.', 1)[1].lower() if '.' in file.name else "wav"
                filename = f"{filename}.{extension}"
                save_path = os.path.join(AUDIO_UPLOAD_FOLDER, filename)
                shutil.copy2(file.name, save_path)
            else:
                # If it's a direct file object or bytes
                extension = "wav"
                filename = f"{filename}.{extension}"
                save_path = os.path.join(AUDIO_UPLOAD_FOLDER, filename)
                with open(save_path, 'wb') as f:
                    if isinstance(file, bytes):
                        f.write(file)
                    else:
                        f.write(file.read())
            
            return os.path.join("audio", filename)
        
        return None
    
    @staticmethod
    def image_to_base64(image_path):
        """Convert image to base64 for API transmission"""
        try:
            with open(os.path.join("uploads", image_path), "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return None
    
    @staticmethod
    def audio_to_base64(audio_path):
        """Convert audio to base64 for API transmission"""
        try:
            with open(os.path.join("uploads", audio_path), "rb") as audio_file:
                return base64.b64encode(audio_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting audio to base64: {e}")
            return None
    
    @staticmethod
    def process_image_for_ai(image_path):
        """Process image for AI analysis (resize, enhance, etc)"""
        try:
            full_path = os.path.join("uploads", image_path)
            img = Image.open(full_path)
            
            # Resize if too large for API
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024))
                img.save(full_path)
            
            # Return base64 of processed image
            return MediaProcessor.image_to_base64(image_path)
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None
    
    @staticmethod
    def create_image_description(image_base64, api_client):
        """Create a text description of an image using AI"""
        try:
            # This is a placeholder for the actual implementation
            # In a real implementation, you would call SambaNova's vision API here
            
            # For now, we'll return a placeholder description
            return "An image showing a person demonstrating soft skills in a professional environment."
        except Exception as e:
            logger.error(f"Error creating image description: {e}")
            return "Unable to generate image description."