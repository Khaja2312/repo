# models/question_generator.py
import requests
import json
import re
import random
import logging
import time
import os
from config import (
    SAMBANOVA_API_KEY, 
    SAMBANOVA_API_URL,
    SAMBANOVA_MODEL_NAME,
    ALTERNATIVE_MODELS,
    AVAILABLE_SKILLS,
    AVAILABLE_LEVELS
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self):
        # Configure the SambaNova API
        self.api_key = SAMBANOVA_API_KEY
        self.api_url = SAMBANOVA_API_URL
        self.model_name = SAMBANOVA_MODEL_NAME
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_question(self, skill, level, question_type):
        """Generate a question of the specified type for a specific skill and level"""
        logger.info(f"Generating {question_type} question for {skill} at {level} level")
        
        if question_type == "Text":
            return self._generate_text_question(skill, level)
        elif question_type == "Audio":
            return self._generate_audio_question(skill, level)
        elif question_type == "Image":
            return self._generate_image_question(skill, level)
        else:
            logger.error(f"Unsupported question type: {question_type}")
            return self._generate_fallback_question(skill, level)
    
    def _generate_text_question(self, skill, level):
        """Generate a text-based question"""
        # Create prompt for text question
        prompt = self._create_text_question_prompt(skill, level)
        
        # Try to get a response from the API
        try:
            question_data = self._make_api_request(prompt)
            
            # Validate the response
            if isinstance(question_data, dict) and "question" in question_data and "expected_answer" in question_data:
                return {
                    "question_type": "Text",
                    "question_content": question_data["question"],
                    "expected_answer": question_data["expected_answer"],
                    "media_path": None
                }
        except Exception as e:
            logger.error(f"Error generating text question: {str(e)}")
        
        # If we get here, use fallback
        fallback = self._generate_fallback_question(skill, level)
        return {
            "question_type": "Text",
            "question_content": fallback["question"],
            "expected_answer": fallback["expected_answer"],
            "media_path": None
        }
    
    def _generate_audio_question(self, skill, level):
        """Generate an audio-based question prompt"""
        # For audio questions, we generate a scenario that would be recorded as audio
        # In a real implementation, you might use text-to-speech or pre-recorded prompts
        
        # Create prompt for audio scenario
        prompt = f"""
        Create a realistic audio scenario to assess {skill} at a {level} level.
        
        The scenario should:
        1. Be a situation that would be presented as an audio recording
        2. Require the student to demonstrate their {skill} skills at a {level} level
        3. Be specific and detailed enough for clear assessment
        
        Provide your response in this exact JSON format:
        {{
            "audio_scenario": "Detailed description of what the audio would contain",
            "question": "The specific question to ask the student after they hear the audio",
            "expected_answer": "Key points that should be included in a correct answer"
        }}
        """
        
        try:
            # Get response from API
            response_data = self._make_api_request(prompt)
            
            if isinstance(response_data, dict) and all(k in response_data for k in ["audio_scenario", "question", "expected_answer"]):
                # In a real implementation, you would convert the audio_scenario to actual audio
                # using text-to-speech or have a narrator record it
                
                # For now, we'll just return the text versions
                return {
                    "question_type": "Audio",
                    "question_content": f"Audio Scenario: {response_data['audio_scenario']}\n\nQuestion: {response_data['question']}",
                    "expected_answer": response_data["expected_answer"],
                    "media_path": None  # In a real implementation, this would be the path to the generated audio file
                }
        except Exception as e:
            logger.error(f"Error generating audio question: {str(e)}")
        
        # Fallback for audio questions
        fallback = self._generate_fallback_question(skill, level)
        scenario = f"Imagine you are listening to a conversation about {skill}. The speakers are discussing key aspects and challenges."
        
        return {
            "question_type": "Audio",
            "question_content": f"Audio Scenario: {scenario}\n\nQuestion: {fallback['question']}",
            "expected_answer": fallback["expected_answer"],
            "media_path": None
        }
    
# models/question_generator.py
# Modify the _generate_image_question method:

    def _generate_image_question(self, skill, level):
        """Generate an image-based question prompt"""
        # For image questions, we generate a description of an image along with a question
        
        # Create prompt for image scenario
        prompt = f"""
        Create a detailed description of an image that could be used to assess {skill} at a {level} level.
        
        The image description should:
        1. Be clear and visualizable
        2. Relate directly to {skill}
        3. Present a scenario appropriate for {level} assessment
        
        Provide your response in this exact JSON format:
        {{
            "image_description": "Detailed description of what the image would show",
            "question": "The specific question to ask the student about the image",
            "expected_answer": "Key points that should be included in a correct answer"
        }}
        """
        
        try:
            # Get response from API
            response_data = self._make_api_request(prompt)
            
            if isinstance(response_data, dict) and all(k in response_data for k in ["image_description", "question", "expected_answer"]):
                # In a real implementation, you would generate or select an actual image
                # based on the description
                
                # Return the question data
                full_question = f"Look at the image and answer the following question:\n\n{response_data['question']}"
                
                return {
                    "question_type": "Image",
                    "question_content": full_question,
                    "expected_answer": response_data["expected_answer"],
                    "image_description": response_data["image_description"],
                    "media_path": None  # This will be generated in app.py
                }
        except Exception as e:
            logger.error(f"Error generating image question: {str(e)}")
        
        # Fallback for image questions
        fallback = self._generate_fallback_question(skill, level)
        image_desc = f"A professional workplace scene showing people demonstrating {skill} in different ways."
        
        return {
            "question_type": "Image",
            "question_content": f"Look at the image and answer: {fallback['question']}",
            "expected_answer": fallback["expected_answer"],
            "image_description": image_desc,
            "media_path": None
        }
    
    def _create_text_question_prompt(self, skill, level):
        """Create a prompt for generating a text question"""
        return f"""
        As an expert educator, create a single assessment question to evaluate a student's knowledge of {skill} at a {level} level.
        
        The question should:
        1. Be clear and direct
        2. Be appropriate for the {level} level
        3. Focus specifically on {skill}
        4. Be answerable in 1-3 paragraphs
        
        Provide your response in this exact JSON format:
        {{
            "question": "The complete question text",
            "expected_answer": "Key points that should be included in a correct answer"
        }}
        
        The JSON must be valid. No markdown formatting. No additional text before or after the JSON.
        """
    
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
                    "temperature": 0.7
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
        raise Exception("All models failed to generate a question")
    
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
    
    def _generate_fallback_question(self, skill, level):
        """Generate a fallback question when API fails"""
        fallback_questions = {
            "Beginner": {
                "question": f"Explain the core concepts of {skill} at a beginner level. What are the fundamental ideas someone new to {skill} should understand?",
                "expected_answer": f"A good answer should cover the basic principles of {skill}, define key terminology, and explain foundational concepts without advanced jargon. The answer should be accessible to someone with no prior knowledge of {skill}."
            },
            "Intermediate": {
                "question": f"Describe the practical applications of {skill} at an intermediate level. How would you implement {skill} techniques in real-world scenarios?",
                "expected_answer": f"A good answer should demonstrate clear understanding of {skill} concepts, explain how to apply them in practice, include examples of common use cases, and show awareness of limitations or challenges when implementing {skill}."
            },
            "Advanced": {
                "question": f"Analyze how {skill} has evolved over time and discuss current cutting-edge developments. What advanced techniques distinguish expert practitioners in this field?",
                "expected_answer": f"A comprehensive answer should demonstrate deep knowledge of {skill}, including its historical development, current state-of-the-art techniques, ability to critically evaluate different approaches, and awareness of ongoing research or innovations in the field."
            }
        }
        
        # Default to intermediate if level not found
        level_key = level if level in fallback_questions else "Intermediate"
        return fallback_questions[level_key]