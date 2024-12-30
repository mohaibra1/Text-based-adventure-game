character = []
bag = []
difficulty = []
def welcome():
    print('***Welcome to the Journey to Mount Qaf***') # write your code here

def show_options():
    print("1. Start a new game (START)")
    print("2. Load your progress (LOAD)")
    print("3. Quit the game (QUIT)")

def choose_difficulty():
    while True:
        print("Choose your difficulty:")
        print("1. Easy")
        print("2. Medium")
        print("3. Hard")
        choice = input()
        if choice.lower() not in ['1', '2', '3', 'easy', 'medium', 'hard']:
            print("Invalid choice. Please try again.")
        else:
            difficulty.append(choice.lower())
            break

def new_game():
    while True:
        username = input("Enter a username ('/b' to go back): ")
        if username == '/b':
            break
        else:
            print("Create your character:")
            name = input("Name: ")
            species = input("Species: ")
            gender = input("Gender: ")
            character.extend([name,species, gender])
            print("Pack your bag for the journey:")
            snack = input("Snack: ")
            weapon = input("Weapon: ")
            tool = input("Tool: ")
            bag.extend([snack, weapon, tool])
            choose_difficulty()
            print(f"Good luck on your journey, {username}")
            print(f"Your character: {name},{species},{gender}")
            print(f"Your inventory: {snack},{weapon}, {tool}")
            print(f"Your difficulty: {difficulty[0]}")
            break

def game():
    welcome()
    print()  # Add a blank line for better readability
    show_options()

    while True:
        choice = input()

        if choice.lower() in ('1', 'start'):
            new_game() # write your code here
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