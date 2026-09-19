"""
Geometry tools for LLM function-calling.

Each tool computes an area, perimeter/circumference, or volume for a
common shape given its dimensions.
"""

import math


def circle_area(radius: float) -> float:
    """
    Compute the area of a circle given its radius.

    Call this tool for requests like "what is the area of a circle
    with radius X".

    Few-shot examples (phrase -> tool call):
        "What is the area of a circle with radius 5?"
                                            -> circle_area(5)
    """
    return math.pi * radius ** 2


def circle_circumference(radius: float) -> float:
    """
    Compute the circumference of a circle given its radius.

    Call this tool for requests like "what is the circumference/
    perimeter of a circle with radius X" or "how far around is a
    circle of radius X".

    Few-shot examples (phrase -> tool call):
        "What is the circumference of a circle with radius 5?"
                                            -> circle_circumference(5)
    """
    return 2 * math.pi * radius


def rectangle_area(length: float, width: float) -> float:
    """
    Compute the area of a rectangle given its length and width.

    Call this tool for requests like "what is the area of a
    rectangle that is X by Y".

    Few-shot examples (phrase -> tool call):
        "What is the area of a 4 by 6 rectangle?"
                                    -> rectangle_area(4, 6)
    """
    return length * width


def rectangle_perimeter(length: float, width: float) -> float:
    """
    Compute the perimeter of a rectangle given its length and width.

    Call this tool for requests like "what is the perimeter of a
    rectangle that is X by Y" or "how much fencing to go around a
    rectangle X by Y".

    Few-shot examples (phrase -> tool call):
        "What is the perimeter of a 4 by 6 rectangle?"
                                    -> rectangle_perimeter(4, 6)
    """
    return 2 * (length + width)


def square_area(side: float) -> float:
    """
    Compute the area of a square given the length of one side.

    Call this tool for requests like "what is the area of a square
    with side X".

    Few-shot examples (phrase -> tool call):
        "What is the area of a square with side 7?"
                                            -> square_area(7)
    """
    return side ** 2


def square_perimeter(side: float) -> float:
    """
    Compute the perimeter of a square given the length of one side.

    Call this tool for requests like "what is the perimeter of a
    square with side X".

    Few-shot examples (phrase -> tool call):
        "What is the perimeter of a square with side 7?"
                                            -> square_perimeter(7)
    """
    return 4 * side


def triangle_area(base: float, height: float) -> float:
    """
    Compute the area of a triangle given its base and height.

    Call this tool for requests like "what is the area of a triangle
    with base X and height Y".

    Few-shot examples (phrase -> tool call):
        "What is the area of a triangle with base 6 and height 4?"
                                    -> triangle_area(6, 4)
    """
    return 0.5 * base * height


def sphere_volume(radius: float) -> float:
    """
    Compute the volume of a sphere given its radius.

    Call this tool for requests like "what is the volume of a
    sphere with radius X".

    Few-shot examples (phrase -> tool call):
        "What is the volume of a sphere with radius 3?"
                                            -> sphere_volume(3)
    """
    return (4 / 3) * math.pi * radius ** 3


def cube_volume(side: float) -> float:
    """
    Compute the volume of a cube given the length of one side.

    Call this tool for requests like "what is the volume of a cube
    with side X".

    Few-shot examples (phrase -> tool call):
        "What is the volume of a cube with side 3?"
                                            -> cube_volume(3)
    """
    return side ** 3


def cylinder_volume(radius: float, height: float) -> float:
    """
    Compute the volume of a cylinder given its radius and height.

    Call this tool for requests like "what is the volume of a
    cylinder with radius X and height Y".

    Few-shot examples (phrase -> tool call):
        "What is the volume of a cylinder with radius 2 and height 10?"
                                    -> cylinder_volume(2, 10)
    """
    return math.pi * radius ** 2 * height