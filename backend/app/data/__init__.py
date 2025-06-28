"""
Data module for the Sales Assistant API Backend.

This module contains data structures and predefined content used throughout
the application, including canonical questions, templates, and configuration data.
"""

from .canonical_questions import (
    get_canonical_questions_list,
    get_questions_by_category,
    get_total_questions_count,
    search_questions_by_keyword
)

__all__ = [
    'get_canonical_questions_list',
    'get_questions_by_category', 
    'get_total_questions_count',
    'search_questions_by_keyword'
]