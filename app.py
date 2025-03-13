import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import logging

from dotenv import load_dotenv
load_dotenv()

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "a-default-secret-key"

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Import functions after app and db are defined
from database_utils import load_database_schema, verify_query, explain_query
from sql_generator import generate_sql_from_nl, call_gemini_api as generator_call_gemini, get_last_token_count, get_total_tokens
from sql_corrector import correct_sql_query, call_gemini_api as corrector_call_gemini


# Initialize database
with app.app_context():
    import models
    db.create_all()

# Update environment variable reference from app context
if not os.environ.get("GEMINI_API_KEY"):
    logger = logging.getLogger(__name__)
    logger.warning("GEMINI_API_KEY environment variable not set")

# Utility function to evaluate query complexity
def evaluate_complexity(sql_query):
    """Evaluate the complexity of a SQL query and return the appropriate level."""
    sql_lower = sql_query.lower()
    
    # Advanced: Complex joins, window functions, CTEs, etc.
    advanced_patterns = [
        'partition by', 'over (', 'with ', ' as (select', 
        'recursive', 'rollup', 'cube', 'grouping sets',
        'lateral', 'unnest', 'json_', 'lag(', 'lead(', 'rank()', 'dense_rank()',
        'row_number()', 'ntile(', 'case when'
    ]
    
    # Intermediate: Joins, subqueries, aggregations, etc.
    intermediate_patterns = [
        'inner join', 'left join', 'right join', 'full join',
        'group by', 'having', '(select', 'union', 'intersect', 'except',
        'order by', 'limit', 'offset', 'distinct', 'count(', 'sum(', 'avg('
    ]
    
    # Check for advanced patterns
    for pattern in advanced_patterns:
        if pattern in sql_lower:
            return 'advanced'
    
    # Check for intermediate patterns
    for pattern in intermediate_patterns:
        if pattern in sql_lower:
            return 'intermediate'
    
    # Default to beginner
    return 'beginner'

# Initialize default learning path if needed
def init_learning_path():
    """Initialize the learning path with predefined challenges."""
    from models import LearningPathChallenge
    
    # Only add challenges if none exist
    if db.session.query(LearningPathChallenge).count() == 0:
        challenges = [
            {
                'title': 'Basic SELECT Queries',
                'short_description': 'Learn how to retrieve data using SELECT statements',
                'description': 'This challenge introduces the fundamental SELECT statement in SQL, which is used to retrieve data from a database.',
                'task': 'Write a query to select all columns from the "customers" table.',
                'hint': 'Use the asterisk (*) to select all columns.',
                'solution': 'SELECT * FROM customers;',
                'complexity': 'beginner',
                'order': 1
            },
            {
                'title': 'Filtering with WHERE',
                'short_description': 'Filter data using the WHERE clause',
                'description': 'The WHERE clause allows you to filter records based on specific conditions.',
                'task': 'Write a query to select all customers who are located in "United States".',
                'hint': 'Use the WHERE clause with the country column.',
                'solution': 'SELECT * FROM customers WHERE country = \'United States\';',
                'complexity': 'beginner',
                'order': 2
            },
            {
                'title': 'Sorting with ORDER BY',
                'short_description': 'Learn to sort query results',
                'description': 'The ORDER BY clause is used to sort the result set based on specified columns.',
                'task': 'Write a query to select all products, sorted by price from highest to lowest.',
                'hint': 'Use ORDER BY with the DESC keyword.',
                'solution': 'SELECT * FROM products ORDER BY price DESC;',
                'complexity': 'beginner',
                'order': 3
            },
            {
                'title': 'Basic Joins',
                'short_description': 'Combine data from multiple tables',
                'description': 'Joins allow you to combine rows from two or more tables based on a related column.',
                'task': 'Write a query to select customer names and their order dates from the customers and orders tables.',
                'hint': 'Use INNER JOIN with the customer_id columns.',
                'solution': 'SELECT customers.name, orders.order_date FROM customers INNER JOIN orders ON customers.id = orders.customer_id;',
                'complexity': 'intermediate',
                'order': 4
            },
            {
                'title': 'Aggregate Functions',
                'short_description': 'Calculate summary values like sum, average, etc.',
                'description': 'Aggregate functions perform calculations on a set of values and return a single value.',
                'task': 'Write a query to calculate the average order value and the total revenue from all orders.',
                'hint': 'Use AVG() and SUM() functions.',
                'solution': 'SELECT AVG(amount) as average_order, SUM(amount) as total_revenue FROM orders;',
                'complexity': 'intermediate',
                'order': 5
            },
            {
                'title': 'Subqueries',
                'short_description': 'Use nested queries for complex operations',
                'description': 'A subquery is a query within another query, allowing you to perform more complex operations.',
                'task': 'Write a query to find customers who have placed orders with a value higher than the average order value.',
                'hint': 'Use a subquery with the AVG function inside a WHERE clause.',
                'solution': 'SELECT customers.* FROM customers JOIN orders ON customers.id = orders.customer_id WHERE orders.amount > (SELECT AVG(amount) FROM orders);',
                'complexity': 'advanced',
                'order': 6
            },
            {
                'title': 'Common Table Expressions (CTEs)',
                'short_description': 'Simplify complex queries with CTEs',
                'description': 'Common Table Expressions (CTEs) provide a way to write auxiliary statements for use in a larger query.',
                'task': 'Use a CTE to list the top 3 products by sales volume along with their total revenue.',
                'hint': 'Use WITH followed by a SELECT statement that joins order_items and products.',
                'solution': 'WITH ProductSales AS (SELECT product_id, SUM(quantity) as total_sold, SUM(quantity * price) as revenue FROM order_items GROUP BY product_id) SELECT products.name, ps.total_sold, ps.revenue FROM ProductSales ps JOIN products ON ps.product_id = products.id ORDER BY ps.total_sold DESC LIMIT 3;',
                'complexity': 'advanced',
                'order': 7
            }
        ]
        
        for challenge_data in challenges:
            challenge = LearningPathChallenge(**challenge_data)
            db.session.add(challenge)
        
        db.session.commit()

# Routes
@app.route('/')
def landing():
    """Render the landing page."""
    return render_template('landing.html')

@app.route('/index')
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/generate')
def generate_page():
    """Render the SQL generation page."""
    return render_template('generate.html')

@app.route('/correct')
def correct_page():
    """Render the SQL correction page."""
    return render_template('correct.html')

@app.route('/api/generate', methods=['POST'])
def generate_sql():
    """API endpoint for generating SQL from natural language."""
    data = request.get_json()
    nl_query = data.get('nl_query', '')
    
    if not nl_query:
        return jsonify({'error': 'No natural language query provided'}), 400
    
    try:
        # Get database schema
        schema_info = load_database_schema()
        
        # Generate SQL
        sql_query = generate_sql_from_nl(nl_query, schema_info)
        
        # Evaluate complexity
        complexity = evaluate_complexity(sql_query)
        
        return jsonify({
            'nl_query': nl_query,
            'sql_query': sql_query,
            'token_count': get_last_token_count(),
            'complexity': complexity
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/correct', methods=['POST'])
def correct_sql():
    """API endpoint for correcting SQL queries."""
    data = request.get_json()
    incorrect_sql = data.get('incorrect_sql', '')
    
    if not incorrect_sql:
        return jsonify({'error': 'No SQL query provided'}), 400
    
    try:
        # Get database schema
        schema_info = load_database_schema()
        
        # Correct SQL
        corrected_sql = correct_sql_query(incorrect_sql, schema_info)
        
        # Evaluate complexity
        complexity = evaluate_complexity(corrected_sql)
        
        return jsonify({
            'incorrect_sql': incorrect_sql,
            'corrected_sql': corrected_sql,
            'token_count': get_last_token_count(),
            'complexity': complexity
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-generate', methods=['POST'])
def batch_generate():
    """API endpoint for batch generating SQL from natural language."""
    data = request.get_json()
    nl_queries = data.get('nl_queries', [])
    
    if not nl_queries:
        return jsonify({'error': 'No natural language queries provided'}), 400
    
    try:
        # Get database schema
        schema_info = load_database_schema()
        
        results = []
        for query in nl_queries:
            # Generate SQL
            sql_query = generate_sql_from_nl(query, schema_info)
            complexity = evaluate_complexity(sql_query)
            
            results.append({
                'nl_query': query,
                'sql_query': sql_query,
                'complexity': complexity
            })
        
        return jsonify({
            'results': results,
            'total_token_count': get_total_tokens()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-correct', methods=['POST'])
def batch_correct():
    """API endpoint for batch correcting SQL queries."""
    data = request.get_json()
    sql_queries = data.get('sql_queries', [])
    
    if not sql_queries:
        return jsonify({'error': 'No SQL queries provided'}), 400
    
    try:
        # Get database schema
        schema_info = load_database_schema()
        
        results = []
        for query in sql_queries:
            # Correct SQL
            corrected_sql = correct_sql_query(query, schema_info)
            complexity = evaluate_complexity(corrected_sql)
            
            results.append({
                'incorrect_sql': query,
                'corrected_sql': corrected_sql,
                'complexity': complexity
            })
        
        return jsonify({
            'results': results,
            'total_token_count': get_total_tokens()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/schema')
def get_schema():
    """API endpoint to retrieve database schema information."""
    try:
        schema_info = load_database_schema()
        return jsonify(schema_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/playground')
def playground_page():
    """Render the SQL playground page."""
    return render_template('playground.html')

@app.route('/learning-path')
def learning_path_page():
    """Render the SQL learning path page."""
    # Initialize learning path if needed
    init_learning_path()
    return render_template('learning_path.html')

@app.route('/favorites')
def favorites_page():
    """Render the saved/favorite queries page."""
    return render_template('favorites.html')

@app.route('/api/save-query', methods=['POST'])
def save_query():
    """API endpoint to save a query to favorites."""
    from models import SavedQuery
    
    data = request.get_json()
    
    required_fields = ['query_text', 'title']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({
                'success': False,
                'error': f'Missing required field: {field}'
            }), 400
    
    try:
        new_query = SavedQuery(
            title=data['title'],
            query_text=data['query_text'],
            nl_query=data.get('nl_query', ''),
            complexity=data.get('complexity', 'beginner'),
            tags=data.get('tags', '')
        )
        
        db.session.add(new_query)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'id': new_query.id,
            'message': 'Query saved successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get-saved-queries')
def get_saved_queries():
    """API endpoint to retrieve all saved queries."""
    from models import SavedQuery
    
    try:
        queries = SavedQuery.query.order_by(SavedQuery.created_at.desc()).all()
        return jsonify([query.to_dict() for query in queries])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-query/<int:query_id>', methods=['DELETE'])
def delete_query(query_id):
    """API endpoint to delete a saved query."""
    from models import SavedQuery
    
    try:
        query = SavedQuery.query.get(query_id)
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query not found'
            }), 404
        
        db.session.delete(query)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Query deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/verify-query', methods=['POST'])
def verify_query_api():
    """API endpoint to verify SQL syntax."""
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No SQL query provided'}), 400
    
    try:
        is_valid, error = verify_query(query)
        return jsonify({
            'is_valid': is_valid,
            'error': error
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/explain-query', methods=['POST'])
def explain_query_api():
    """API endpoint to explain a SQL query execution plan."""
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No SQL query provided'}), 400
    
    try:
        success, explanation = explain_query(query)
        return jsonify({
            'success': success,
            'explanation': explanation
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning-path')
def get_learning_path():
    """API endpoint to retrieve learning path challenges."""
    from models import LearningPathChallenge, CompletedChallenge
    
    try:
        # Get active challenges in order
        challenges = LearningPathChallenge.query.filter_by(active=True).order_by(LearningPathChallenge.order).all()
        
        # Get completed challenges
        completed = CompletedChallenge.query.all()
        completed_ids = [c.challenge_id for c in completed]
        
        return jsonify({
            'challenges': [challenge.to_dict() for challenge in challenges],
            'completed_challenges': completed_ids
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complete-challenge/<int:challenge_id>', methods=['POST'])
def complete_challenge(challenge_id):
    """API endpoint to mark a challenge as completed."""
    from models import LearningPathChallenge, CompletedChallenge
    
    try:
        # Check if challenge exists
        challenge = LearningPathChallenge.query.get(challenge_id)
        if not challenge:
            return jsonify({
                'success': False,
                'error': 'Challenge not found'
            }), 404
        
        # Check if already completed
        existing = CompletedChallenge.query.filter_by(challenge_id=challenge_id).first()
        if not existing:
            # Mark as completed
            completed = CompletedChallenge(challenge_id=challenge_id)
            db.session.add(completed)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Challenge marked as completed'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sql-buddy-tip', methods=['POST'])
def sql_buddy_tip():
    """API endpoint to get a tip from SQL Buddy based on query or context."""
    data = request.get_json()
    query = data.get('query', '')
    user_message = data.get('user_message', '')
    
    if not query and not user_message:
        return jsonify({'error': 'No query or message provided'}), 400
    
    try:
        # For a basic implementation, we'll use the Together AI API with a custom prompt
        # In a real implementation, you might have a dedicated model or endpoint
        prompt = f"""You are SQL Buddy, a helpful AI assistant for SQL. 
        
        User Query: {query}
        
        User Message: {user_message}
        
        Provide a brief, helpful tip related to the SQL query or respond to the user's question.
        Focus on best practices, optimizations, or explanations of SQL concepts.
        Keep your response under 250 words and make it practical and educational.
        """
        
        response = generator_call_gemini(prompt, temperature=0.7, max_tokens=500)
        
        return jsonify({
            'tip': response.strip()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)