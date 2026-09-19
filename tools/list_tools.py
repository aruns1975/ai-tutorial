"""
List/collection tools for LLM function-calling.

Each tool operates on a list of numbers (or, where noted, a list of
generic items) and returns a plain result.
"""


def sort_list(items: list[float], descending: bool = False) -> list[float]:
    """
    Sort a list of numbers in ascending order by default.

    Call this tool for requests like "sort these numbers" or "put
    these numbers in order". Set descending=True for requests like
    "sort from highest to lowest" or "sort descending".

    Few-shot examples (phrase -> tool call):
        "Sort [3, 1, 2]."                  -> sort_list([3, 1, 2])
        "Sort [3, 1, 2] from highest to lowest."
                                            -> sort_list([3, 1, 2], descending=True)
    """
    return sorted(items, reverse=descending)


def reverse_list(items: list) -> list:
    """
    Reverse the order of items in a list.

    Call this tool for requests like "reverse this list" or "flip the
    order of these items".

    Few-shot examples (phrase -> tool call):
        "Reverse [1, 2, 3]."               -> reverse_list([1, 2, 3])
    """
    return list(reversed(items))


def find_max(items: list[float]) -> float:
    """
    Return the largest value in a list of numbers.

    Call this tool for requests like "what is the biggest/highest/
    largest number in this list" or "find the maximum".

    Few-shot examples (phrase -> tool call):
        "What's the largest number in [4, 9, 2, 7]?"
                                            -> find_max([4, 9, 2, 7])
    """
    return max(items)


def find_min(items: list[float]) -> float:
    """
    Return the smallest value in a list of numbers.

    Call this tool for requests like "what is the smallest/lowest
    number in this list" or "find the minimum".

    Few-shot examples (phrase -> tool call):
        "What's the smallest number in [4, 9, 2, 7]?"
                                            -> find_min([4, 9, 2, 7])
    """
    return min(items)


def sum_list(items: list[float]) -> float:
    """
    Return the sum of all numbers in a list.

    Call this tool for requests like "add up all these numbers", "what
    is the total of this list", or "sum these values" — this is the
    list-input counterpart of `math_tools.adder` for more than two
    numbers.

    Few-shot examples (phrase -> tool call):
        "What is the total of [1, 2, 3, 4]?"
                                            -> sum_list([1, 2, 3, 4])
    """
    return sum(items)


def average_list(items: list[float]) -> float:
    """
    Return the arithmetic mean (average) of a list of numbers.

    Call this tool for requests like "what is the average of these
    numbers" or "find the mean".

    Few-shot examples (phrase -> tool call):
        "What's the average of [10, 20, 30]?"
                                            -> average_list([10, 20, 30])
    """
    return sum(items) / len(items)


def unique_items(items: list) -> list:
    """
    Return the list of unique items, preserving first-seen order.

    Call this tool for requests like "remove duplicates from this
    list" or "what are the distinct values here".

    Few-shot examples (phrase -> tool call):
        "Remove duplicates from [1, 2, 2, 3, 1]."
                                            -> unique_items([1, 2, 2, 3, 1])
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def filter_greater_than(items: list[float], threshold: float) -> list[float]:
    """
    Return only the numbers in a list that are greater than a
    threshold.

    Call this tool for requests like "which of these numbers are
    greater than X" or "filter out anything below X".

    Few-shot examples (phrase -> tool call):
        "Which numbers in [1, 5, 10, 15] are greater than 6?"
                            -> filter_greater_than([1, 5, 10, 15], 6)
    """
    return [item for item in items if item > threshold]


def list_length(items: list) -> int:
    """
    Return the number of items in a list.

    Call this tool for requests like "how many items are in this
    list" or "count these entries".

    Few-shot examples (phrase -> tool call):
        "How many items are in [1, 2, 3, 4, 5]?"
                                            -> list_length([1, 2, 3, 4, 5])
    """
    return len(items)


def flatten_list(items: list[list]) -> list:
    """
    Flatten a list of lists into a single list, one level deep.

    Call this tool for requests like "flatten this nested list" or
    "combine these sublists into one list".

    Few-shot examples (phrase -> tool call):
        "Flatten [[1, 2], [3, 4], [5]]."
                                    -> flatten_list([[1, 2], [3, 4], [5]])
    """
    return [item for sublist in items for item in sublist]