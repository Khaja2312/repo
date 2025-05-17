# models/evaluator.py
import requests
import json
import re
import logging
import time
from models.transcription import AudioTranscriber
from models.media_processor import MediaProcessor
from config import (
    SAMBANOVA_API_KEY,
    SAMBANOVA_API_URL,
    SAMBANOVA_MODEL_NAME,
    ALTERNATIVE_MODELS
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Evaluator:
    def __init__(self):
        # Configure the SambaNova API
        self.api_key = SAMBANOVA_API_KEY
        self.api_url = SAMBANOVA_API_URL
        self.model_name = SAMBANOVA_MODEL_NAME
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Initialize helpers
        self.transcriber = AudioTranscriber()
        self.media_processor = MediaProcessor()
    
    def evaluate_answer(self, question, expected_answer, student_answer, skill, level, 
                        question_type="Text", answer_type="Text", 
                        question_media=None, answer_media=None):
        """Evaluate a student's answer with support for different media types"""
        logger.info(f"Evaluating {answer_type} answer for {question_type} question about {skill} at {level} level")
        
        # Process the question and answer based on their types
        processed_question = self._process_question(question, question_type, question_media)
        processed_answer = self._process_answer(student_answer, answer_type, answer_media)
        
        # Create the evaluation prompt
        prompt = self._create_evaluation_prompt(
            processed_question, 
            expected_answer, 
            processed_answer,
            skill, 
            level,
            question_type,
            answer_type
        )
        
        # Try to get an evaluation from the API
        try:
            evaluation = self._make_api_request(prompt)
            
            if isinstance(evaluation, dict) and "is_correct" in evaluation and "explanation" in evaluation:
                is_correct = evaluation["is_correct"]
                # Convert string "true"/"false" to boolean if needed
                if isinstance(is_correct, str):
                    is_correct = is_correct.lower() == "true"
                
                explanation = evaluation["explanation"]
                return is_correct, explanation
        except Exception as e:
            logger.error(f"Error during evaluation: {str(e)}")
        
        # If API fails, use fallback evaluation
        return self._fallback_evaluation(processed_answer, expected_answer)
    
    def _process_question(self, question, question_type, media_path):
        """Process the question based on its type"""
        if question_type == "Text":
            return question
        
        elif question_type == "Audio" and media_path:
            # Transcribe audio question if needed
            audio_transcript = self.transcriber.transcribe_audio(media_path)
            return f"{question}\n\nAudio Transcript: {audio_transcript}"
        
        elif question_type == "Image" and media_path:
            # Process image if needed
            image_base64 = self.media_processor.process_image_for_ai(media_path)
            # In a real implementation, you might analyze the image with AI
            return question
        
        # Default case
        return question
    
    def _process_answer(self, answer, answer_type, media_path):
        """Process the student's answer based on its type"""
        if answer_type == "Text":
            return answer
        
        elif answer_type == "Audio" and media_path:
            # Transcribe audio answer
            audio_transcript = self.transcriber.transcribe_audio(media_path)
            return f"Audio Answer Transcript: {audio_transcript}"
        
        elif answer_type == "Image" and media_path:
            # Process image answer
            image_base64 = self.media_processor.process_image_for_ai(media_path)
            # You would use AI to analyze the image
            image_description = self.media_processor.create_image_description(image_base64, None)
            return f"Image Answer Description: {image_description}"
        
        # Default case or if media processing failed
        return answer if answer else "No answer provided"
    
    def _create_evaluation_prompt(self, question, expected_answer, student_answer, 
                                 skill, level, question_type, answer_type):
        """Create a detailed prompt for evaluation"""
        prompt = f"""
        You are an expert educator evaluating student responses for soft skills assessment.
        
        Assessment Context:
        - Skill being assessed: {skill}
        - Level: {level}
        - Question Type: {question_type}
        - Answer Type: {answer_type}
        
        Question: {question}
        
        Expected key points in the answer: {expected_answer}
        
        Student's answer: {student_answer}
        
        Your task:
        1. Compare the student's answer to the expected key points
        2. Determine if the student demonstrated sufficient understanding of {skill} at a {level} level
        3. Provide a brief explanation justifying your assessment
        4. Consider the format of both question and answer in your evaluation
        
        Return ONLY this exact JSON format with no additional text:
        {{
            "is_correct": true or false,
            "explanation": "Brief explanation of the assessment"
        }}
        """
        return prompt
    
    def _make_api_request(self, prompt):
        """Make API request and handle response with retry logic"""
        # Try each model name in order
        all_models = [self.model_name] + ALTERNATIVE_MODELS
        
        for model_name in all_models:
            try:
                logger.info(f"Trying model: {model_name}")
                
                # Prepare the payload
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "max_tokens": 512,
                    "temperature": 0.3  # Lower temperature for more consistent evaluations
                }
                
                # Make the request
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                # Check if successful
                if response.status_code == 200:
                    logger.info(f"Successful API call with model: {model_name}")
                    
                    # Parse the response
                    response_data = response.json()
                    
                    # Extract content based on API structure
                    if "text" in response_data:
                        content = response_data.get("text", "")
                    elif "choices" in response_data and len(response_data["choices"]) > 0:
                        content = response_data["choices"][0].get("text", "")
                    else:
                        content = str(response_data)
                    
                    # Extract and parse JSON
                    json_str = self._extract_json(content)
                    return json.loads(json_str)
                
                elif response.status_code == 404 and "Model not found" in response.text:
                    # Try next model
                    logger.warning(f"Model {model_name} not found, trying next model")
                    continue
                
                else:
                    logger.error(f"API error with model {model_name}: {response.status_code}, {response.text}")
                    
            except Exception as e:
                logger.error(f"Exception with model {model_name}: {str(e)}")
        
        # If all models fail, raise exception
        raise Exception("All models failed to evaluate the answer")
    
    def _extract_json(self, text):
        """Extract JSON from text that might contain other content"""
        # Try to find JSON content within the text
        if "```json" in text and "```" in text:
            return text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_candidate = text.split("```")[1].split("```")[0].strip()
            # Verify it's actually JSON
            try:
                json.loads(json_candidate)
                return json_candidate
            except:
                pass
        
        # Try to find content between curly braces
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
            
        # If all else fails, return the original text
        return text
    
    def _fallback_evaluation(self, student_answer, expected_answer):
        """Simple fallback evaluation when API fails"""
        student_text = student_answer.lower()
        expected_text = expected_answer.lower()
        
        # Generate keywords from expected answer
        expected_keywords = set(word.strip('.,;:()[]{}"\'"')
                               for word in expected_text.split()
                               if len(word) > 4)  # Only consider words longer than 4 chars
        
        # Count matching keywords in student answer
        matching_keywords = 0
        for keyword in expected_keywords:
            if keyword in student_text:
                matching_keywords += 1
        
        # Calculate match percentage
        match_percentage = matching_keywords / len(expected_keywords) if expected_keywords else 0
        
        # Determine if answer is correct based on keyword matches
        is_correct = match_percentage >= 0.5  # At least 50% keyword match
        
        if is_correct:
            explanation = f"The answer covers approximately {int(match_percentage * 100)}% of the key concepts expected."
        else:
            explanation = f"The answer is missing several important concepts (only covers about {int(match_percentage * 100)}% of expected key points)."
        
        return is_correct, explanation