def main():
    addition = __import__('addition').add
    subtraction = __import__('subtraction').subtract

    print("Addition: ", addition(5, 3))
    print("Subtraction: ", subtraction(5, 3))

if __name__ == '__main__':
    main()