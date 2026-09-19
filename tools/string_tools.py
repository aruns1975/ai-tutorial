"""
String manipulation tools for LLM function-calling.

Each tool takes plain string (and occasionally simple scalar) inputs
and returns a plain result, so they can be safely exposed to a
function-calling LLM without any side effects.
"""


def reverse_text(text: str) -> str:
    """
    Reverse the characters in a string.

    Call this tool for requests like "reverse this word/sentence" or
    "flip the string backwards".

    Few-shot examples (phrase -> tool call):
        "Reverse the word 'hello'."        -> reverse_text("hello")
        "What does 'stressed' look like backwards?"
                                            -> reverse_text("stressed")
    """
    return text[::-1]


def to_uppercase(text: str) -> str:
    """
    Convert a string to all uppercase letters.

    Call this tool for requests like "make this uppercase", "shout
    this", or "capitalize everything" (when the intent is ALL CAPS,
    not just the first letter — for that, use `capitalize_words`).

    Few-shot examples (phrase -> tool call):
        "Make 'hello world' uppercase."    -> to_uppercase("hello world")
        "Shout 'good morning'."            -> to_uppercase("good morning")
    """
    return text.upper()


def to_lowercase(text: str) -> str:
    """
    Convert a string to all lowercase letters.

    Call this tool for requests like "make this lowercase" or "remove
    the capitalization".

    Few-shot examples (phrase -> tool call):
        "Make 'HELLO WORLD' lowercase."    -> to_lowercase("HELLO WORLD")
        "Lowercase this: 'GoodMorning'."   -> to_lowercase("GoodMorning")
    """
    return text.lower()


def capitalize_words(text: str) -> str:
    """
    Capitalize the first letter of every word in a string (title case).

    Call this tool for requests like "title case this", "capitalize
    each word", or "make this look like a proper title/name".

    Few-shot examples (phrase -> tool call):
        "Title case 'the great gatsby'."   -> capitalize_words("the great gatsby")
        "Capitalize each word in 'john smith'."
                                            -> capitalize_words("john smith")
    """
    return text.title()


def word_count(text: str) -> int:
    """
    Count the number of whitespace-separated words in a string.

    Call this tool for requests like "how many words are in this
    sentence/paragraph" or "count the words".

    Few-shot examples (phrase -> tool call):
        "How many words are in 'the quick brown fox'?"
                                            -> word_count("the quick brown fox")
    """
    return len(text.split())


def char_count(text: str, include_spaces: bool = True) -> int:
    """
    Count the number of characters in a string.

    Call this tool for requests like "how many characters/letters are
    in this string". Set include_spaces=False when the request
    specifically excludes spaces (e.g. "how many letters, not counting
    spaces").

    Few-shot examples (phrase -> tool call):
        "How many characters are in 'hello world'?"
                                            -> char_count("hello world")
        "How many letters in 'hello world', not counting spaces?"
                                            -> char_count("hello world", include_spaces=False)
    """
    if include_spaces:
        return len(text)
    return len(text.replace(" ", ""))


def contains_substring(text: str, substring: str) -> bool:
    """
    Check whether a string contains another string.

    Call this tool for requests like "does this text contain X", "is
    the word X in this sentence", or "search for X in this string".

    Few-shot examples (phrase -> tool call):
        "Does 'hello world' contain 'wor'?"
                                    -> contains_substring("hello world", "wor")
        "Is 'cat' in 'concatenate'?"
                                    -> contains_substring("concatenate", "cat")
    """
    return substring in text


def replace_substring(text: str, old: str, new: str) -> str:
    """
    Replace every occurrence of one substring with another.

    Call this tool for requests like "replace X with Y in this text"
    or "swap out every X for Y".

    Few-shot examples (phrase -> tool call):
        "Replace 'cat' with 'dog' in 'I have a cat'."
                            -> replace_substring("I have a cat", "cat", "dog")
    """
    return text.replace(old, new)


def split_text(text: str, delimiter: str = " ") -> list[str]:
    """
    Split a string into a list of parts using a delimiter.

    Call this tool for requests like "split this into words/parts" or
    "break this comma-separated string apart". Defaults to splitting
    on whitespace when no delimiter is specified.

    Few-shot examples (phrase -> tool call):
        "Split 'a,b,c' by comma."          -> split_text("a,b,c", ",")
        "Split this sentence into words: 'hi there friend'."
                                            -> split_text("hi there friend")
    """
    return text.split(delimiter)


def is_palindrome(text: str) -> bool:
    """
    Check whether a string reads the same forwards and backwards,
    ignoring case and spaces.

    Call this tool for requests like "is this word/phrase a
    palindrome" or "does this read the same backwards".

    Few-shot examples (phrase -> tool call):
        "Is 'racecar' a palindrome?"       -> is_palindrome("racecar")
        "Does 'A man a plan a canal Panama' read the same backwards?"
                                    -> is_palindrome("A man a plan a canal Panama")
    """
    cleaned = text.lower().replace(" ", "")
    return cleaned == cleaned[::-1]