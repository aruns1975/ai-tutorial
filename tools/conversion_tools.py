"""
Unit conversion tools for LLM function-calling.

Each pair of tools converts explicitly in one direction — do not try
to reuse one for the reverse conversion with inverted arguments; call
the matching tool for the direction actually being asked about.
"""


def celsius_to_fahrenheit(celsius: float) -> float:
    """
    Convert a temperature from Celsius to Fahrenheit.

    Call this tool for requests like "what is X Celsius in
    Fahrenheit" or "convert X C to F".

    Few-shot examples (phrase -> tool call):
        "What is 100 Celsius in Fahrenheit?"
                                    -> celsius_to_fahrenheit(100)
    """
    return celsius * 9 / 5 + 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    Convert a temperature from Fahrenheit to Celsius.

    Call this tool for requests like "what is X Fahrenheit in
    Celsius" or "convert X F to C".

    Few-shot examples (phrase -> tool call):
        "What is 212 Fahrenheit in Celsius?"
                                    -> fahrenheit_to_celsius(212)
    """
    return (fahrenheit - 32) * 5 / 9


def km_to_miles(kilometers: float) -> float:
    """
    Convert a distance from kilometers to miles.

    Call this tool for requests like "how many miles is X km" or
    "convert X kilometers to miles".

    Few-shot examples (phrase -> tool call):
        "How many miles is 10 km?"         -> km_to_miles(10)
    """
    return kilometers * 0.621371


def miles_to_km(miles: float) -> float:
    """
    Convert a distance from miles to kilometers.

    Call this tool for requests like "how many kilometers is X
    miles" or "convert X miles to km".

    Few-shot examples (phrase -> tool call):
        "How many km is 5 miles?"          -> miles_to_km(5)
    """
    return miles / 0.621371


def kg_to_pounds(kilograms: float) -> float:
    """
    Convert a mass from kilograms to pounds.

    Call this tool for requests like "how many pounds is X kg" or
    "convert X kilograms to lbs".

    Few-shot examples (phrase -> tool call):
        "How many pounds is 70 kg?"        -> kg_to_pounds(70)
    """
    return kilograms * 2.20462


def pounds_to_kg(pounds: float) -> float:
    """
    Convert a mass from pounds to kilograms.

    Call this tool for requests like "how many kilograms is X
    pounds" or "convert X lbs to kg".

    Few-shot examples (phrase -> tool call):
        "How many kg is 150 pounds?"       -> pounds_to_kg(150)
    """
    return pounds / 2.20462


def meters_to_feet(meters: float) -> float:
    """
    Convert a length from meters to feet.

    Call this tool for requests like "how many feet is X meters" or
    "convert X m to ft".

    Few-shot examples (phrase -> tool call):
        "How many feet is 2 meters?"       -> meters_to_feet(2)
    """
    return meters * 3.28084


def feet_to_meters(feet: float) -> float:
    """
    Convert a length from feet to meters.

    Call this tool for requests like "how many meters is X feet" or
    "convert X ft to m".

    Few-shot examples (phrase -> tool call):
        "How many meters is 6 feet?"       -> feet_to_meters(6)
    """
    return feet / 3.28084


def liters_to_gallons(liters: float) -> float:
    """
    Convert a volume from liters to US gallons.

    Call this tool for requests like "how many gallons is X liters"
    or "convert X L to gal".

    Few-shot examples (phrase -> tool call):
        "How many gallons is 20 liters?"   -> liters_to_gallons(20)
    """
    return liters * 0.264172


def gallons_to_liters(gallons: float) -> float:
    """
    Convert a volume from US gallons to liters.

    Call this tool for requests like "how many liters is X gallons"
    or "convert X gal to L".

    Few-shot examples (phrase -> tool call):
        "How many liters is 5 gallons?"    -> gallons_to_liters(5)
    """
    return gallons / 0.264172