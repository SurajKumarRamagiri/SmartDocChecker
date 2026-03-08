"""
Application-wide constants.
"""

SUPPORTED_FILE_TYPES = [".pdf", ".docx", ".txt"]

MAX_FILE_SIZE_MB = 10

# Shared stop-word set used across NLP components for content-word overlap,
# deduplication, and description generation.
STOP_WORDS = frozenset({
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'am',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
    'should', 'may', 'might', 'can', 'could', 'of', 'in', 'to', 'for',
    'and', 'or', 'but', 'on', 'at', 'by', 'with', 'from', 'as', 'into',
    'that', 'this', 'it', 'its', 'not', 'no', 'if', 'so', 'than', 'then',
    'such', 'also', 'any', 'all', 'each', 'every', 'both', 'other',
    'must', 'minimum', 'maximum',
})
