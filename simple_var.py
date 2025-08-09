def set_variable(value):
    """
    Set the global variable x to the given value.
    
    Args:
        value: The value to set x to
    """
    global x
    x = value


def get_variable():
    """
    Get the current value of the global variable x.
    
    Returns:
        The current value of x
    """
    return x


def reset_variable():
    """
    Reset the global variable x to its default value (1).
    """
    global x
    x = 1


def is_variable_set():
    """
    Check if the variable x has been set (not at default value).
    
    Returns:
        bool: True if x has been set to a value other than 1, False otherwise
    """
    return x != 1

# Initialize the variable
x = 1

# Example usage (uncomment to test)
# if __name__ == "__main__":
#     print(f"Initial value: {get_variable()}")
#     set_variable(10)
#     print(f"After setting to 10: {get_variable()}")
#     reset_variable()
#     print(f"After reset: {get_variable()}")
