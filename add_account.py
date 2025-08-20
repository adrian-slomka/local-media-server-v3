from database_utils import add_account

if __name__ == "__main__":
    while True:
        try:
            is_admin = int(input('Give admin permissions? (1) Yes, (0) No: '))
            is_adult = int(input('Disable adult content? (1) Yes, (0) No: '))
            if is_admin not in (0, 1) or is_adult not in (0, 1):
                raise ValueError("Input must be 0 or 1")
            
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
