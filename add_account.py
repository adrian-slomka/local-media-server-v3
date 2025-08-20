from database_utils import add_account

if __name__ == "__main__":
    while True:
        try:

            is_admin = int(input("Give admin permissions? (1 = Yes, 0 = No): "))
            if is_admin not in (0, 1):
                raise ValueError

            disable_adult = int(input("Disable adult content? (1 = Yes, 0 = No): "))
            if disable_adult not in (0, 1):
                raise ValueError
            
            # Flip logic: is_adult = not disable_adult
            is_adult = int(not disable_adult)


            password = str(input('Enter a password for the new account: '))
            confirmation = str(input('Confirm the password: '))

            if password == confirmation:
                # add_account(password, is_admin, is_adult)
                print('New user account has been created successfully.')
                break
            else:
                print('Passwords do not match. Please try again.')
                
        except Exception as e:
            print(f'An error occurred: {e}')
