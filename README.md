# BirthdaySync

Small project to pull my contacts birthdays from Google contacts and post recurring reminders to Remember the Milk


## Dependencies

```
python3 -m pip install -r requirements.txt
```

or from scratch

```
python3 -m pip install google-auth-oauthlib
python3 -m pip install google-api-python-client
```


## Workflow

The `app.py` script does the following:

- Retrieves a list of all your Google contacts
- Formats this into a RTM string to give a reminder for each contacts birthday
- Emails this string to your RTM inbox for it to be converted into a task


## Setup

The following files are expected:

- `secrets/config.json`

```
{
    "email_me": "<your email address>",
    "email_rtm": "<your RTM import email address>"
}
```

- `secrets/credentials.json`
A credentials file as downloaded from the google cloud console. The corresponding project must have the people and email apis enabled. 

Required scopes include:

- `auth/contacts.readonly`
- `auth/gmail.send`

