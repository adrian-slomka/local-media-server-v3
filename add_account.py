from database_utils import add_account

if __name__ == "__main__":
    while True:
        try:
            password = str(input('Enter a password for the new account: '))
            confirmation = str(input('Confirm the password: '))
            if password == confirmation:
                add_account(password)
                print('New user account has been created successfully.')
                break
            else:
                print('Passwords do not match. Please try again.')
        except Exception as e:
            print(f'An error occurred: {e}')
