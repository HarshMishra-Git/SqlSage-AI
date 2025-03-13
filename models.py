from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from app import db

class SavedQuery(db.Model):
    """Model for user-saved SQL queries."""
    __tablename__ = 'saved_queries'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    query_text = Column(Text, nullable=False)
    nl_query = Column(Text)
    complexity = Column(String(50), default='beginner')  # beginner, intermediate, advanced
    tags = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SavedQuery {self.id}: {self.title}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'query_text': self.query_text,
            'nl_query': self.nl_query,
            'complexity': self.complexity,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class LearningPathChallenge(db.Model):
    """Model for SQL learning path challenges."""
    __tablename__ = 'learning_path_challenges'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    short_description = Column(String(255))
    description = Column(Text)
    task = Column(Text, nullable=False)
    hint = Column(Text)
    solution = Column(Text)  # Example solution
    complexity = Column(String(50), default='beginner')  # beginner, intermediate, advanced
    order = Column(Integer, nullable=False)  # Order in the learning path
    active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<LearningPathChallenge {self.id}: {self.title}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'short_description': self.short_description,
            'description': self.description,
            'task': self.task,
            'hint': self.hint,
            'complexity': self.complexity,
            'order': self.order
        }

class CompletedChallenge(db.Model):
    """Model to track completed learning path challenges."""
    __tablename__ = 'completed_challenges'
    
    id = Column(Integer, primary_key=True)
    challenge_id = Column(Integer, ForeignKey('learning_path_challenges.id'), nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CompletedChallenge {self.id}: challenge_id={self.challenge_id}>"