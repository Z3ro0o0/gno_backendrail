import resend

resend.api_key = "re_3HrFPxTW_3PZssqZHbW3wNViQmwuiZund"

params = {
    "from": "Ong Trucking <onboarding@jeronpos.com>",
    "to": ["taptopup@myglobalmail.eu"],
    "subject": "Hello from Resend!",
    "html": "<p>It works 🎉</p>",
}

response: resend.Email = resend.Emails.send(params)
print(response)