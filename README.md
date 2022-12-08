# Roast My Looker Instance

[Try it out!](https://www.roastmylookerinstance.com)

**Roast My Looker Instance** is a web app with a snarky chatbot that examines your Looker instance and reports on issues like abandoned dashboards, inactive users, and slow Explores.

Provide Looker API credentials for a user with Admin role, and see how your Looker instance holds up to the withering criticism.

## How does it work?

RMLI is a Remix/React app with a Python (FastAPI) backend. The backend fetches data from the Looker API and System Activity Explore and calculates stats used determine the chatbot messages. API credentials are stored securely in Google Cloud Platform in Google Secret Manager where they automatically expire after one day.

## Why did we build it?

At [Spectacles](https://spectacles.dev), we care a lot about development best practices and Looker administration. We built this project for the Looker 2022 Hackathon as a fun way to identify areas of improvement for Looker admins.

Built with ❤️ (and snark) by the team at [Spectacles](https://spectacles.dev)
