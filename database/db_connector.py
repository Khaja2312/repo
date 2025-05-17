# database/db_connector.py
import mysql.connector
from mysql.connector import Error
import sys
import os
import logging
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConnector:
    def __init__(self):
        self.connection = None
        self.try_connect()
    
    def try_connect(self):
        """Establish connection to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
            )
            
            if self.connection.is_connected():
                logger.info("Connected to MySQL database")
                # Create tables if they don't exist
                self._create_tables()
        except Error as e:
            logger.error(f"Error connecting to MySQL database: {e}")
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = self.connection.cursor()
        try:
            # Read schema.sql
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            with open(schema_path, 'r') as f:
                sql_script = f.read()
            
            # Execute each statement in the schema
            for statement in sql_script.split(';'):
                if statement.strip():
                    cursor.execute(statement)
            
            self.connection.commit()
            logger.info("Database tables created or verified")
        except Error as e:
            logger.error(f"Error creating tables: {e}")
        finally:
            cursor.close()
    
    def execute_query(self, query, params=None, fetch=False):
        """Execute a SQL query with optional parameters"""
        if not self.connection or not self.connection.is_connected():
            self.try_connect()
            if not self.connection or not self.connection.is_connected():
                return None
        
        cursor = self.connection.cursor(dictionary=True)
        result = None
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                result = cursor.fetchall()
            else:
                self.connection.commit()
                result = cursor.lastrowid
        except Error as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
        finally:
            cursor.close()
        
        return result
    
    # Questions CRUD operations
    def save_question(self, skill, level, question_type, question_content, expected_answer, media_path=None):
        """Save a generated question to the database"""
        query = """
        INSERT INTO questions (skill, level, question_type, question_content, expected_answer, media_path)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (skill, level, question_type, question_content, expected_answer, media_path)
        return self.execute_query(query, params)
    
    def get_questions(self, skill=None, level=None, question_type=None, limit=10):
        """Get questions with optional filtering"""
        query = "SELECT * FROM questions WHERE 1=1"
        params = []
        
        if skill:
            query += " AND skill = %s"
            params.append(skill)
        
        if level:
            query += " AND level = %s"
            params.append(level)
        
        if question_type:
            query += " AND question_type = %s"
            params.append(question_type)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, params, fetch=True)
    
    def get_question_by_id(self, question_id):
        """Get a specific question by ID"""
        query = "SELECT * FROM questions WHERE id = %s"
        params = (question_id,)
        result = self.execute_query(query, params, fetch=True)
        return result[0] if result else None
    
    # Answers CRUD operations
    def save_answer(self, question_id, answer_content, answer_type, media_path=None):
        """Save a student answer to the database"""
        query = """
        INSERT INTO answers (question_id, answer_content, answer_type, media_path)
        VALUES (%s, %s, %s, %s)
        """
        params = (question_id, answer_content, answer_type, media_path)
        return self.execute_query(query, params)
    
    def get_answers_by_question(self, question_id):
        """Get all answers for a specific question"""
        query = "SELECT * FROM answers WHERE question_id = %s ORDER BY created_at DESC"
        params = (question_id,)
        return self.execute_query(query, params, fetch=True)
    
    # Evaluations CRUD operations
    def save_evaluation(self, answer_id, is_correct, explanation):
        """Save an evaluation for an answer"""
        query = """
        INSERT INTO evaluations (answer_id, is_correct, explanation)
        VALUES (%s, %s, %s)
        """
        params = (answer_id, is_correct, explanation)
        return self.execute_query(query, params)
    
    def get_evaluation_by_answer(self, answer_id):
        """Get evaluation for a specific answer"""
        query = "SELECT * FROM evaluations WHERE answer_id = %s"
        params = (answer_id,)
        result = self.execute_query(query, params, fetch=True)
        return result[0] if result else None
    
    def close_connection(self):
        """Close the database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")