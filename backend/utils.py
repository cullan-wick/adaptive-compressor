def calculate_word_budget(time_limit_mins: int, wpm: int) -> int:
    """
    Calculates the maximum number of words allowed.
    """
    return time_limit_mins * wpm

def count_words(text: str) -> int:
    """
    Simple whitespace splitter to estimate word count.
    """
    return len(text.split())