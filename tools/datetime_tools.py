"""
Date and time tools for LLM function-calling.

Dates are accepted/returned as ISO-format strings ("YYYY-MM-DD") so
they are easy for an LLM to read and produce without ambiguity.
"""

from datetime import datetime, timedelta


def current_date() -> str:
    """
    Return today's date as an ISO string (YYYY-MM-DD).

    Call this tool for requests like "what is today's date" or "what
    day is it".

    Few-shot examples (phrase -> tool call):
        "What's today's date?"             -> current_date()
    """
    return datetime.now().date().isoformat()


def current_time() -> str:
    """
    Return the current time as an HH:MM:SS string (24-hour clock).

    Call this tool for requests like "what time is it right now".

    Few-shot examples (phrase -> tool call):
        "What time is it?"                 -> current_time()
    """
    return datetime.now().strftime("%H:%M:%S")


def add_days(date: str, days: int) -> str:
    """
    Add (or subtract, with a negative value) a number of days to a date.

    Call this tool for requests like "what date is 10 days after X",
    "X days from now", or "what was the date 5 days before X".

    Few-shot examples (phrase -> tool call):
        "What date is 10 days after 2026-01-01?"
                                    -> add_days("2026-01-01", 10)
        "What was the date 5 days before 2026-03-10?"
                                    -> add_days("2026-03-10", -5)
    """
    d = datetime.fromisoformat(date)
    return (d + timedelta(days=days)).date().isoformat()


def days_between(start_date: str, end_date: str) -> int:
    """
    Return the number of days between two ISO-format dates.

    Call this tool for requests like "how many days are between X and
    Y" or "how many days until X" (using today's date as start_date).

    Few-shot examples (phrase -> tool call):
        "How many days between 2026-01-01 and 2026-01-31?"
                            -> days_between("2026-01-01", "2026-01-31")
    """
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    return (end - start).days


def day_of_week(date: str) -> str:
    """
    Return the day of the week (e.g. "Monday") for an ISO-format date.

    Call this tool for requests like "what day of the week was/is X"
    or "what weekday does X fall on".

    Few-shot examples (phrase -> tool call):
        "What day of the week is 2026-12-25?"
                                    -> day_of_week("2026-12-25")
    """
    return datetime.fromisoformat(date).strftime("%A")


def is_leap_year(year: int) -> bool:
    """
    Check whether a given year is a leap year.

    Call this tool for requests like "is X a leap year" or "does X
    have 366 days".

    Few-shot examples (phrase -> tool call):
        "Is 2024 a leap year?"             -> is_leap_year(2024)
        "Does 2026 have 366 days?"         -> is_leap_year(2026)
    """
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def format_date(date: str, output_format: str) -> str:
    """
    Reformat an ISO-format date string using a strftime pattern.

    Call this tool for requests like "format this date as
    DD/MM/YYYY" or "write this date out in a different style".

    Few-shot examples (phrase -> tool call):
        "Format 2026-09-19 as DD/MM/YYYY."
                        -> format_date("2026-09-19", "%d/%m/%Y")
        "Write 2026-09-19 as 'September 19, 2026'."
                        -> format_date("2026-09-19", "%B %d, %Y")
    """
    return datetime.fromisoformat(date).strftime(output_format)


def add_hours(datetime_str: str, hours: float) -> str:
    """
    Add (or subtract, with a negative value) hours to an ISO-format
    datetime string.

    Call this tool for requests like "what time is it 3 hours from
    now" or "what was the time 2 hours before X".

    Few-shot examples (phrase -> tool call):
        "What is 3 hours after 2026-09-19T10:00:00?"
                        -> add_hours("2026-09-19T10:00:00", 3)
        "What was the time 2 hours before 2026-09-19T10:00:00?"
                        -> add_hours("2026-09-19T10:00:00", -2)
    """
    dt = datetime.fromisoformat(datetime_str)
    return (dt + timedelta(hours=hours)).isoformat()