def welcome():
    print('***Welcome to the Journey to Mount Qaf***') # write your code here

def show_options():
    print("1. Start a new game (START)")
    print("2. Load your progress (LOAD)")
    print("3. Quit the game (QUIT)")

def game():
    welcome()
    print()  # Add a blank line for better readability
    show_options()

    while True:
        choice = input()

        if choice.lower() in ('1', 'start'):
            print('Starting a new game...') # write your code here
            break
        elif choice.lower() in ('2', 'load'):
            print('No saved data found!') # write your code here
            break
        elif choice.lower() in ('3', 'quit'):
            print('Goodbye!')
            break
        else:
            print('Unknown input! Please enter a valid one.')

game()