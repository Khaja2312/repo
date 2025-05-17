# app.py
import gradio as gr
import os
import uuid
import time
import logging
from datetime import datetime
import numpy as np
from PIL import Image
import tempfile
import textwrap

# Import our modules
from config import (
    AVAILABLE_SKILLS, 
    AVAILABLE_LEVELS, 
    QUESTION_TYPES, 
    UPLOAD_FOLDER,
    IMAGE_UPLOAD_FOLDER,
    AUDIO_UPLOAD_FOLDER
)
from models.question_generator import QuestionGenerator
from models.evaluator import Evaluator
from models.media_processor import MediaProcessor
from models.transcription import AudioTranscriber
from database.db_connector import DatabaseConnector

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_UPLOAD_FOLDER, exist_ok=True)

# Initialize components
question_generator = QuestionGenerator()
evaluator = Evaluator()
media_processor = MediaProcessor()
transcriber = AudioTranscriber()
db = DatabaseConnector()

# Session management
active_sessions = {}

def generate_session_id():
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def start_session(skill, level):
    """Start a new assessment session"""
    session_id = generate_session_id()
    active_sessions[session_id] = {
        "skill": skill,
        "level": level,
        "start_time": datetime.now(),
        "questions": [],
        "current_question_index": -1,
        "answers": [],
        "evaluations": [],
        "score": 0
    }
    
    # Store in database
    db.execute_query(
        "INSERT INTO sessions (session_id, skill, level) VALUES (%s, %s, %s)",
        (session_id, skill, level)
    )
    
    return session_id

def end_session(session_id):
    """End an assessment session"""
    if session_id in active_sessions:
        session = active_sessions[session_id]
        session["end_time"] = datetime.now()
        
        # Calculate final score
        if len(session["evaluations"]) > 0:
            correct_answers = sum(1 for eval_result in session["evaluations"] if eval_result[0])
            total_questions = len(session["evaluations"])
            session["score"] = int((correct_answers / total_questions) * 100)
        
        # Update database
        db.execute_query(
            "UPDATE sessions SET end_time = NOW(), score = %s WHERE session_id = %s",
            (session["score"], session_id)
        )
        
        return session["score"]
    
    return 0

def create_placeholder_image(description, skill, level):
    """Create a placeholder image with text description (temporary solution)"""
    # Create a blank image with text
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color=(240, 240, 240))
    
    try:
        # Add text to the image
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(image)
        
        # Try to use a system font
        font_size = 20
        title_font_size = 30
        font = None
        title_font = None
        
        # Try common font locations
        possible_fonts = [
            "arial.ttf",
            "Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/Windows/Fonts/Arial.ttf",
            "C:/Windows/Fonts/Arial.ttf"
        ]
        
        for font_path in possible_fonts:
            try:
                font = ImageFont.truetype(font_path, font_size)
                title_font = ImageFont.truetype(font_path, title_font_size)
                break
            except:
                continue
        
        # Fallback to default font if none of the above work
        if font is None:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()
        
        # Draw title
        title = f"{skill} Question ({level} Level)"
        draw.text((width//2 - 150, 50), title, fill=(0, 0, 0), font=title_font)
        
        # Draw description - wrap text
        wrapped_text = textwrap.fill(description, width=60)
        y_position = 120
        for line in wrapped_text.split('\n'):
            draw.text((50, y_position), line, fill=(0, 0, 0), font=font)
            y_position += 30
        
        # Draw a border around the image
        draw.rectangle([(0, 0), (width-1, height-1)], outline=(0, 0, 0), width=2)
        
        # Add a hint at the bottom
        draw.text((50, height - 50), "This is a placeholder image. In a real app, this would be a relevant image.", 
                  fill=(100, 100, 100), font=font)
        
    except Exception as e:
        logger.error(f"Error creating placeholder image: {e}")
    
    return image

def generate_question(skill, level, question_type):
    """Generate a question and display it"""
    try:
        # Log request
        logger.info(f"Generating {question_type} question for {skill} at {level} level")
        
        # Generate question
        question_data = question_generator.generate_question(skill, level, question_type)
        
        # Display the question
        if question_type == "Text":
            return question_data["question_content"], question_data["expected_answer"], "", None, None
        
        elif question_type == "Audio":
            # In a real implementation, this would include actual audio
            # For now, we'll use a placeholder description
            audio_description = question_data["question_content"]
            return question_data["question_content"], question_data["expected_answer"], audio_description, None, None
        
        elif question_type == "Image":
            # For Image questions, we need to generate an actual image based on the description
            image_description = question_data.get("image_description", "")
            
            # Check if we have a description
            if not image_description and "question_content" in question_data:
                # Try to extract description from question content if needed
                parts = question_data["question_content"].split("Look at the image")
                if len(parts) > 1:
                    image_description = parts[0].strip()
                else:
                    image_description = "A visual representation of " + skill
            
            logger.info(f"Creating image for: {image_description}")
            
            # Create a placeholder image (you would replace this with actual image generation)
            placeholder_img = create_placeholder_image(image_description, skill, level)
            
            # Save the placeholder image
            img_path = os.path.join(IMAGE_UPLOAD_FOLDER, f"question_{uuid.uuid4()}.png")
            placeholder_img.save(img_path)
            
            # Return the question with the image
            relative_path = os.path.relpath(img_path, start=os.path.dirname(UPLOAD_FOLDER))
            
            return question_data["question_content"], question_data["expected_answer"], image_description, relative_path, placeholder_img
    
    except Exception as e:
        logger.error(f"Error generating question: {str(e)}")
        return f"Error generating question: {str(e)}", "", "", None, None

def submit_answer(question, expected_answer, student_answer, skill, level, question_type, answer_type, question_media=None, answer_media=None):
    """Submit and evaluate a student's answer"""
    try:
        # Process media if provided
        answer_media_path = None
        if answer_type == "Audio" and answer_media is not None:
            # Save the audio file
            if isinstance(answer_media, str) and os.path.exists(answer_media):
                # It's already a file path
                answer_media_path = media_processor.save_uploaded_file(answer_media, "audio")
                student_answer = f"Audio answer submitted (file: {os.path.basename(answer_media)})"
            else:
                # It's audio data
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                    temp_audio.write(answer_media)
                    answer_media_path = media_processor.save_uploaded_file(temp_audio.name, "audio")
                    student_answer = f"Audio answer submitted"
        
        elif answer_type == "Image" and answer_media is not None:
            # Save the image file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
                answer_media.save(temp_img.name)
                answer_media_path = media_processor.save_uploaded_file(temp_img.name, "image")
                student_answer = "Image answer submitted"
        
        # Evaluate the answer
        is_correct, explanation = evaluator.evaluate_answer(
            question, 
            expected_answer, 
            student_answer, 
            skill, 
            level,
            question_type,
            answer_type,
            question_media,
            answer_media_path
        )
        
        # Format the result
        result_text = f"Result: {'Correct' if is_correct else 'Needs Improvement'}\n\n{explanation}"
        
        # Return the evaluation result
        return result_text, is_correct
        
    except Exception as e:
        logger.error(f"Error evaluating answer: {str(e)}")
        return f"Error evaluating answer: {str(e)}", False

# Define the Gradio UI
def create_ui():
    with gr.Blocks(title="Advanced Soft Skills Assessment System") as interface:
        gr.Markdown("# Advanced Soft Skills Assessment System")
        gr.Markdown("### Generate and answer questions to assess soft skills with support for text, audio, and images")
        
        # Session state variables (hidden)
        session_id = gr.State("")
        current_question = gr.State("")
        current_expected_answer = gr.State("")
        current_question_type = gr.State("Text")
        current_question_media = gr.State(None)
        
        with gr.Tab("Generate Question"):
            with gr.Row():
                skill = gr.Dropdown(choices=AVAILABLE_SKILLS, label="Skill to Assess")
                level = gr.Dropdown(choices=AVAILABLE_LEVELS, label="Difficulty Level")
                q_type = gr.Dropdown(choices=QUESTION_TYPES, label="Question Type", value="Text")
            
            generate_btn = gr.Button("Generate Question")
            
            with gr.Row():
                question_display = gr.Textbox(label="Question", lines=4, interactive=False)
                expected_answer = gr.Textbox(label="Expected Answer (hidden in real assessment)", lines=4, interactive=False)
            
            with gr.Row():
                # Update these components to better handle different media types
                media_display = gr.Textbox(label="Media Description", visible=False)
                # Preview area for images and audio
                image_preview = gr.Image(label="Question Image", visible=False, type="pil")
                audio_preview = gr.Audio(label="Question Audio", visible=False)
            
            # Function to toggle media components based on question type
            def toggle_media_components(question_type):
                """Toggle visibility of media components based on question type"""
                if question_type == "Text":
                    return (
                        gr.update(visible=False),  # media_display
                        gr.update(visible=False),  # image_preview
                        gr.update(visible=False)   # audio_preview
                    )
                elif question_type == "Audio":
                    return (
                        gr.update(visible=True),   # media_display
                        gr.update(visible=False),  # image_preview
                        gr.update(visible=True)    # audio_preview
                    )
                elif question_type == "Image":
                    return (
                        gr.update(visible=True),   # media_display
                        gr.update(visible=True),   # image_preview
                        gr.update(visible=False)   # audio_preview
                    )
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False)
                )
            
            q_type.change(
                toggle_media_components, 
                inputs=[q_type], 
                outputs=[media_display, image_preview, audio_preview]
            )
        
        # Modified Answer & Evaluate tab with separate content for each answer type
        with gr.Tab("Answer & Evaluate"):
            with gr.Tabs() as answer_tabs:
                with gr.TabItem("Text Answer"):
                    text_answer = gr.Textbox(label="Your Text Answer", lines=6)
                    text_submit_btn = gr.Button("Submit Text Answer")
                
                with gr.TabItem("Audio Answer"):
                    audio_answer = gr.Audio(label="Your Audio Answer", source="microphone", type="filepath")
                    audio_submit_btn = gr.Button("Submit Audio Answer")
                
                with gr.TabItem("Image Answer"):
                    image_answer = gr.Image(label="Your Image Answer", type="pil")
                    image_submit_btn = gr.Button("Submit Image Answer")
            
            evaluation_result = gr.Textbox(label="Evaluation", lines=4, interactive=False)
            
            # Define submission functions for each type
            def submit_text_answer(question, expected_answer, answer, skill, level, q_type, q_media):
                result, is_correct = submit_answer(
                    question, expected_answer, answer, 
                    skill, level, q_type, "Text", q_media, None
                )
                return result
                
            def submit_audio_answer(question, expected_answer, answer, skill, level, q_type, q_media):
                result, is_correct = submit_answer(
                    question, expected_answer, "", 
                    skill, level, q_type, "Audio", q_media, answer
                )
                return result
                
            def submit_image_answer(question, expected_answer, answer, skill, level, q_type, q_media):
                result, is_correct = submit_answer(
                    question, expected_answer, "", 
                    skill, level, q_type, "Image", q_media, answer
                )
                return result
            
            # Set up submission handlers
            text_submit_btn.click(
                submit_text_answer,
                inputs=[
                    current_question, current_expected_answer, 
                    text_answer, skill, level, current_question_type, current_question_media
                ],
                outputs=[evaluation_result]
            )
            
            audio_submit_btn.click(
                submit_audio_answer,
                inputs=[
                    current_question, current_expected_answer, 
                    audio_answer, skill, level, current_question_type, current_question_media
                ],
                outputs=[evaluation_result]
            )
            
            image_submit_btn.click(
                submit_image_answer,
                inputs=[
                    current_question, current_expected_answer, 
                    image_answer, skill, level, current_question_type, current_question_media
                ],
                outputs=[evaluation_result]
            )
        
        with gr.Tab("Assessment History"):
            refresh_history_btn = gr.Button("Refresh History")
            history_display = gr.Dataframe(
                headers=["Session ID", "Skill", "Level", "Start Time", "End Time", "Score"],
                datatype=["str", "str", "str", "str", "str", "number"],
                row_count=10
            )
            
            def load_history():
                # Get history from database
                results = db.execute_query(
                    """
                    SELECT session_id, skill, level, 
                           DATE_FORMAT(start_time, '%Y-%m-%d %H:%i:%s') as start_time, 
                           DATE_FORMAT(end_time, '%Y-%m-%d %H:%i:%s') as end_time, 
                           score
                    FROM sessions
                    ORDER BY start_time DESC
                    LIMIT 10
                    """, 
                    fetch=True
                )
                
                if not results:
                    return []
                
                # Format for display
                history_data = []
                for row in results:
                    history_data.append([
                        row["session_id"],
                        row["skill"],
                        row["level"],
                        row["start_time"],
                        row["end_time"] if row["end_time"] else "In Progress",
                        row["score"] if row["score"] is not None else "N/A"
                    ])
                
                return history_data
            
            refresh_history_btn.click(
                load_history,
                inputs=[],
                outputs=[history_display]
            )
        
        # Handle question generation
        def on_generate(skill, level, question_type):
            try:
                # Start a new session
                session_id_val = start_session(skill, level)
                
                # Generate the question
                question, exp_answer, media_desc, media_path, media_preview = generate_question(skill, level, question_type)
                
                # Update the session state
                if session_id_val in active_sessions:
                    active_sessions[session_id_val]["questions"].append({
                        "question": question,
                        "expected_answer": exp_answer,
                        "question_type": question_type,
                        "media": media_path
                    })
                    active_sessions[session_id_val]["current_question_index"] += 1
                
                # Save question to database
                question_id = db.save_question(
                    skill, level, question_type, question, exp_answer, 
                    media_path if media_path else None
                )
                
                # For debugging
                logger.info(f"Question created with media path: {media_path}")
                if media_preview is not None:
                    logger.info(f"Media preview is available of type: {type(media_preview)}")
                
                # Prepare UI updates based on question type
                if question_type == "Image":
                    # For image questions, make the image visible and update its value
                    return (
                        question,
                        exp_answer,
                        gr.update(value=media_desc, visible=True),  # media_description
                        gr.update(value=media_preview, visible=True),  # image_preview
                        gr.update(visible=False),  # audio_preview
                        session_id_val,
                        question,
                        exp_answer,
                        question_type,
                        media_path
                    )
                elif question_type == "Audio":
                    # For audio questions
                    return (
                        question,
                        exp_answer,
                        gr.update(value=media_desc, visible=True),  # media_description
                        gr.update(visible=False),  # image_preview
                        gr.update(value=media_path, visible=True),  # audio_preview
                        session_id_val,
                        question,
                        exp_answer,
                        question_type,
                        media_path
                    )
                else:
                    # For text questions
                    return (
                        question,
                        exp_answer,
                        gr.update(visible=False),  # media_description
                        gr.update(visible=False),  # image_preview
                        gr.update(visible=False),  # audio_preview
                        session_id_val,
                        question,
                        exp_answer,
                        question_type,
                        media_path
                    )
            except Exception as e:
                logger.error(f"Error in on_generate: {str(e)}")
                # Return empty/default values in case of error
                return (
                    f"Error generating question: {str(e)}",
                    "",
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    "",
                    "",
                    "",
                    "Text",
                    None
                )
        
        generate_btn.click(
            on_generate,
            inputs=[skill, level, q_type],
            outputs=[
                question_display, expected_answer, media_display,
                image_preview, audio_preview,
                session_id, current_question, current_expected_answer,
                current_question_type, current_question_media
            ]
        )
        
        # Initial data load for history
        interface.load(load_history, outputs=[history_display])
    
    return interface

# Create and launch the UI
interface = create_ui()
if __name__ == "__main__":
    interface.launch(server_name="0.0.0.0", server_port=7861, share=True)