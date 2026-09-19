"""
Arithmetic tools for LLM function-calling.

These four tools (adder, subtractor, multiplier, divider) each take
exactly two numbers. A user request is rarely handed to you in that
clean a form — it may be a symbolic expression ("3+4"), a natural
language sentence ("increment 4 by 5"), a bare single-number command
("increment 5", which implicitly means "by 1"), or a longer expression
with repeated terms ("5+6+5") that should be decomposed into a
*sequence* of these two-argument tool calls rather than assumed to be
a single call.

General decomposition strategy for a complex/multi-term expression:
    1. Parse it into individual terms and operators, left to right.
    2. If the SAME value appears more than once joined only by "+",
       collapse that run into a single `multiplier` call (value, count)
       before combining it with the remaining terms via `adder`.
    3. Likewise, a value repeatedly subtracted collapses into a single
       `divider`-style reduction (see `divider`'s docstring) — but note
       `divider` answers "how many times does it divide out", not a
       running total; for a running total of repeated subtraction from
       a fixed starting value, chain `subtractor` calls or reduce it to
       one `multiplier` call subtracted once (e.g. "20-5-5-5" ==
       20 - (5*3) -> multiplier(5, 3) then subtractor(20, <result>)).
    4. Only fall back to chaining single-step calls (e.g. repeated
       `adder` calls) when the terms are NOT all identical and can't be
       collapsed.

Few-shot examples (expression -> tool call plan):
    "3+4"                   -> adder(3, 4)
    "5+6"                   -> adder(5, 6)
    "increment 4 by 5"      -> adder(4, 5)
    "increment 5"           -> adder(5, 1)          # bare increment = by 1
    "decrement 5"           -> subtractor(5, 1)      # bare decrement = by 1
    "5+6+5"                 -> multiplier(5, 2) then adder(<result>, 6)
                               # two 5s collapse to 5*2, then + 6
    "4+4+4+3"               -> multiplier(4, 3) then adder(<result>, 3)
    "20-5-5-5"              -> multiplier(5, 3) then subtractor(20, <result>)
"""


def adder(a: int|float, b: int|float) -> float:
    """
    Add two numbers together (a + b).

    Call this tool for any request that means "combine", "increment",
    "increase", "add", "plus", "sum", "total", or "how many in all" —
    even if the word "add" never appears. It also covers a *single-step*
    increment, e.g. "what is a number after it goes up by 5".

    Also recognize the bare symbolic form "a+b" (e.g. "3+4") as a direct
    call, and a bare "increment X" with no explicit amount as an
    implicit "by 1" (increment X by 1).

    Do NOT use this for the same value being added to itself a known
    number of times (e.g. "add 4 to itself 6 times") — that is repeated
    addition and should use `multiplier` instead (see its docstring).
    For a longer expression with repeated terms (e.g. "5+6+5"), see the
    module-level docstring on decomposing multi-term expressions.

    Few-shot examples (phrase -> tool call):
        "What is 7 plus 5?"                    -> adder(7, 5)
        "3+4"                                  -> adder(3, 4)
        "Increase 10 by 3."                    -> adder(10, 3)
        "Increment 4 by 5."                    -> adder(4, 5)
        "Increment 5."                         -> adder(5, 1)
        "If I have 20 apples and get 4 more, how many do I have?"
                                                -> adder(20, 4)
        "Combine 12 and 8."                    -> adder(12, 8)
    """
    return a+b

def subtractor(a: int|float, b: int|float) -> float:
    """
    Subtract the second number from the first (a - b).

    Call this tool for any request that means "decrement", "decrease",
    "minus", "take away", "difference", "reduce by", or "how many are
    left" — even if the word "subtract" never appears. It also covers a
    *single-step* decrement, e.g. "what is a number after it goes down
    by 5".

    Also recognize the bare symbolic form "a-b" (e.g. "9-2") as a direct
    call, and a bare "decrement X" with no explicit amount as an
    implicit "by 1" (decrement X by 1).

    Do NOT use this for the same value being subtracted repeatedly a
    known number of times (e.g. "take 4 away from 20, four times") —
    that is repeated subtraction and should use `divider` instead (see
    its docstring). For a longer expression with repeated terms (e.g.
    "20-5-5-5"), see the module-level docstring on decomposing
    multi-term expressions.

    Few-shot examples (phrase -> tool call):
        "What is 15 minus 6?"                  -> subtractor(15, 6)
        "9-2"                                  -> subtractor(9, 2)
        "Decrease 10 by 3."                    -> subtractor(10, 3)
        "Decrement 4 by 5."                    -> subtractor(4, 5)
        "Decrement 5."                         -> subtractor(5, 1)
        "I had 20 apples and gave away 4, how many are left?"
                                                -> subtractor(20, 4)
        "What is the difference between 50 and 30?"
                                                -> subtractor(50, 30)
    """
    return a-b

def multiplier(a: int|float, b: int|float) -> float:
    """
    Multiply two numbers together (a * b).

    Call this tool for any request that means "times", "product",
    "double/triple/etc.", "scale by", or "for each ... how many total" —
    even if the word "multiply" never appears.

    This tool is also the correct choice whenever a request describes
    REPEATED ADDITION of the same value: "add 4 to itself 6 times",
    "sum six 4s", "what is 4 added repeatedly 6 times" all mean
    multiplier(4, 6). When parsing a complex expression, first check
    whether it reduces to "the same number added N times" before
    reaching for `adder` in a loop — if so, call this tool once instead.

    Also recognize the bare symbolic form "a*b" (e.g. "6*7") as a direct
    call, and a multi-term addition where the same value repeats (e.g.
    "5+6+5" — see the module-level docstring) as a signal to collapse
    the repeated value into a multiplier call first.

    Few-shot examples (phrase -> tool call):
        "What is 6 times 7?"                       -> multiplier(6, 7)
        "6*7"                                      -> multiplier(6, 7)
        "Add 4 to itself 6 times."                 -> multiplier(4, 6)
        "What do you get if you sum five 3s?"      -> multiplier(3, 5)
        "Double 9."                                -> multiplier(9, 2)
        "Each box has 8 apples, there are 5 boxes, how many apples total?"
                                                    -> multiplier(8, 5)
    """
    return a*b

def divider(a: int|float, b: int|float) -> float:
    """
    Divide the first number by the second (a / b).

    Call this tool for any request that means "quotient", "split into",
    "share equally", "how many times does X go into Y", or "per unit" —
    even if the word "divide" never appears.

    This tool is also the correct choice whenever a request describes
    REPEATED SUBTRACTION of the same value until reaching zero (or
    until it no longer fits): "how many times can you take 5 away from
    20", "keep subtracting 3 from 30 until nothing is left, how many
    steps" both mean divider(20, 5) / divider(30, 3). When parsing a
    complex expression, first check whether it reduces to "the same
    number subtracted repeatedly from a total" before reaching for
    `subtractor` in a loop — if so, call this tool once instead.

    Also recognize the bare symbolic form "a/b" (e.g. "20/4") as a
    direct call.

    Few-shot examples (phrase -> tool call):
        "What is 20 divided by 4?"                     -> divider(20, 4)
        "20/4"                                          -> divider(20, 4)
        "How many times can I subtract 5 from 20?"     -> divider(20, 5)
        "Split 30 into 6 equal groups, how big is each group?"
                                                        -> divider(30, 6)
        "Keep taking 3 away from 21 until it's gone — how many times?"
                                                        -> divider(21, 3)

    Raises:
        ZeroDivisionError: If b is 0.
    """
    return a/b