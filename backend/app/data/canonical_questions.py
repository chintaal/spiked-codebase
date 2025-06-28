"""
Canonical Questions Data Module

Exact questions from the cleaned questions file for cache population.
These are the actual questions that need to be cached for the HealthAssist platform.
"""

# Canonical questions exactly as they appear in questions_cleaned
CANONICAL_QUESTIONS = [
    "Can you provide a high-level overview of the HealthAssist architecture?",
    "What security measures are in place to ensure HIPAA compliance and data privacy?",
    "Can you share examples of how HealthAssist has helped other healthcare organizations improve patient care and reduce costs?",
    "What are the standard service level agreements (SLAs) for HealthAssist support and uptime?",
    "What EMR/EHR systems does HealthAssist seamlessly integrate with?",
    "What API standards are used for integration (e.g., HL7, FHIR)?",
    "Can you elaborate on the integration process with external symptom checkers like Infermedica, Isabel, and Mediktor?",
    "What are the technical requirements for deploying HealthAssist, both on-premise and in the cloud?",
    "How is data synchronization and real-time data updates handled between HealthAssist and integrated systems?",
    "What are the specifications for LLM and Generative AI integration, including supported models and configuration options?",
    "Can you provide details on the authentication methods supported (e.g., OAuth)?",
    "How does HealthAssist handle scalability and performance under high user loads?",
    "What are the backup and disaster recovery procedures for HealthAssist data?",
    "Details on the Channel Integration, specifically Voice Channel, SMS and Web/Mobile Client details?",
    "What database technology is used by HealthAssist to store and manage data?",
    "Can HealthAssist be customized with custom APIs to extend its core functionalities?",
    "Can you explain the NLP engines used (Machine Learning and Fundamental Meaning) and how they are trained and updated?",
    "How does the Few Shot Model work for intent detection?",
    "What is the accuracy rate of intent detection, and how is it measured?",
    "How does HealthAssist handle multilingual support, and what languages are currently supported?",
    "Can HealthAssist adapt to industry specific language such as medical ontologies?",
    "Can you provide a demo of the HealthAssist Workbench and its customization capabilities?",
    "What roles and permissions can be assigned to users in the Workbench?",
    "How can we monitor and analyze the performance of HealthAssist using the dashboard?",
    "What are the steps for publishing configuration changes to the live environment?",
    "Details on Live Agent Transfer and Agent Playbook?",
    "Explain the different configurations options for dynamic conversations?",
    "How is patient data encrypted both at rest and in transit?",
    "What access controls are in place to protect patient data?",
    "How are audit logs managed and retained for compliance purposes?",
    "What data breach notification procedures are in place?",
    "What are the different licensing models available for HealthAssist?",
    "What kind of training and documentation is provided for administrators and users?",
    "What are the support channels available, and what are the response times for different support tiers?",
    "What are the ongoing maintenance and upgrade costs?",
    "List of clients",
    "How does Citibank use kore?",
    "How does Pfizer use kore?"
]

def get_canonical_questions_list():
    """Return the list of canonical questions."""
    return CANONICAL_QUESTIONS.copy()

def get_total_questions_count():
    """Get the total number of canonical questions."""
    return len(CANONICAL_QUESTIONS)

def get_questions_by_category():
    """
    Get canonical questions organized by category.
    Since these are the actual business questions, they're returned as one category.
    """
    return {
        "healthassist": CANONICAL_QUESTIONS
    }

def search_questions_by_keyword(keyword):
    """
    Search for questions containing a specific keyword.
    
    Args:
        keyword (str): The keyword to search for
        
    Returns:
        list: List of questions containing the keyword
    """
    keyword_lower = keyword.lower()
    return [
        question for question in CANONICAL_QUESTIONS
        if keyword_lower in question.lower()
    ]

# Export the main function for backward compatibility
__all__ = [
    'get_canonical_questions_list',
    'get_questions_by_category', 
    'get_total_questions_count',
    'search_questions_by_keyword'
]