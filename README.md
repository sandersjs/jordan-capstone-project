1. Clone the Project
2. pip install -r requirements.txt
3. Setup password hash
4. Add your projects
5. Deploy the application

________________________________________________

Password Hash Instructions


Open your terminal/command prompt in the same folder as your Flask project.
Make sure you’re in the same Python environment where Flask is installed (the one you use to run python app.py).
Paste these two lines and hit Enter:

python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('Capstone2025Theater!', method='pbkdf2:sha256', salt_length=16))"

→ Replace 'YourStrongPasswordHere' with whatever password you actually want (e.g. Capstone2025!Theater).

It will instantly print a long hash that looks like this:
PASSWORD_HASH=pbkdf2:sha256:1000000$a6UYcfFz8bK9mN1pQ2rS3tU4vW5xY6zA$a1b2c3d4e5f6g7h8i9j0kLmNoPqRsTuVwXyZ
Copy that whole string and paste it into your .env file as the value for PASSWORD_HASH=.
In your .env file you put exactly this (no quotes, no extra spaces, no colon at the end):
PASSWORD_HASH=pbkdf2:sha256:1000000$a6UYcfFz8bK9mN1pQ2rS3tU4vW5xY6zA$a1b2c3d4e5f6g7h8i9j0kLmNoPqRsTuVwXyZ

That exact plain-text password you put inside the quotes is the one you must type when the login page asks for the password.

Update Portfolio
1. Remove the data.json file and add your projects once the app is deployed.
2. Or add the data.json file to the .gitignore file so that it is not included in your repository.
   Otherwise it will overwrite any data changes made on the deployed version.