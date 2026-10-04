# Online demo and local research

The online app includes two public Agent Board summaries, six invented messages, and synthetic experiment fixtures.
It runs the same evidence and measurement functions as the local app.
The four downloaded research datasets stay on the research computer.

Reviews and imported experiment files are saved in the visitor's browser storage.
Clearing browser data removes that visitor's saved work. Export important reviews first.
The demo does not synchronize work across devices or browsers.

Submitted review checks and experiment calculations reach the hosted app server.
The server validates and calculates them in temporary memory. The application does not write them to a shared database.
Hosting-provider request logs are separate from application storage.
Do not submit sensitive material through this public demo.

The local app continues to use its own SQLite database and real imported records.
The online app does not read or upload that database.
It does not run recorded code, launch agents, or call model APIs.

## Deployment

The Vercel entry point is `api/index.py`.
Each request uses a fresh synthetic database in memory.
`static/hosted-storage.js` keeps visitor work separate in browser storage.
`.vercelignore` permits only source code, static files, research references, invented fixtures, and the two public message summaries.
It excludes local databases, raw datasets, environment files, screenshots, and private reviews.

From a linked checkout, deploy with `vercel deploy --prod`.
This project uses a direct CLI deployment. GitHub deployment integration is not configured.
Run the tests and inspect the upload allowlist before publishing changes.
