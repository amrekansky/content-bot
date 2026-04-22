<!-- LinkedIn example 2 — English, lowercase, no long dashes or dramatic colons -->

one employee clicked "connect with google" and vercel got breached

no virus. no phishing. no zero-day. just an ai productivity app with oauth access.

i've been thinking about this a lot lately. we're in this weird moment where every tool that makes you more productive, the ai meeting notes, the smart inbox, the calendar assistant, they all ask for the same thing. connect your google account.

and you click allow. because everyone does. because it's convenient. because the onboarding is smooth and the product looks legit.

here's what that actually means. you didn't give them your password. you gave them a token. a long string that tells google this app can act as you. read your emails. access your files. send messages on your behalf.

that token doesn't expire when you change your password. doesn't expire when you forget the app exists. doesn't expire when that startup gets acquired, pivots, or gets hacked.

context ai got hacked. attacker grabbed oauth tokens. used one to walk into a vercel employee's google account. from there straight into vercel's infrastructure. api keys, source code, customer data.

the scary part isn't that context ai got hacked. startups get hacked. the scary part is that one employee's productivity app became the attack vector for an entire company's infrastructure.

go to google right now. security, third-party apps with account access. count how many apps are in that list. now ask yourself, do i actually trust every single one of those companies to protect that access?

vercel trusted context ai.

what's your count, and how many of those apps do you even still use?
